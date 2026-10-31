"""Prepare run outputs and coordinate the independent output writers."""

import datetime
import logging
import os
import time

from qgis.core import QgsProcessingException, QgsVariantUtils

from ..classification import TIERS
from ..domain import (
    METRIC_FIELDS, STAND_SCHEMA_FIELD_CANDIDATES, mapped_metric_ids,
    weighted_summary,
)
from ..grid_indicators import (
    AGE_METRICS, AREA_METRICS, GRID_VOLUME_FIELDS, STAND_VOLUME_FIELDS,
    summarize_indicator_rows,
)
from ...app_logging import LOGGER_NAME
from ...data_attribution import data_attribution
from ...adapters.excel_writer import write_workbook
from ...adapters.result_precision import RESULT_DECIMALS
from ...adapters.geopackage_writer import write_geopackage
from ...adapters.classified_result import create_water_evidence_layer
from ...adapters.serialization import json_default
from ...i18n import tr
from ...adapters.sources import OUT_OF_SCOPE_COVERAGE
from .common import _check_cancelled, _feedback


logger = logging.getLogger(LOGGER_NAME + ".analysis.publishing")


def prepare_publication(inputs, retrieved, classified, run_id):
    """Prepare coverage and run metadata before any output is written."""
    language = inputs["language"]
    output_folder = inputs["output_folder"]
    try:
        os.makedirs(output_folder, exist_ok=True)
        if not os.access(output_folder, os.W_OK):
            raise OSError("folder is not writable")
    except OSError as exc:
        raise QgsProcessingException(tr(language, "error_output_writable", path=exc))

    coverage = [dict(row) for row in classified["coverage"]]
    for row in OUT_OF_SCOPE_COVERAGE:
        excluded = {**row, "scope": "sensitivity_criterion"}
        if row["service_id"] == "peatlands":
            excluded["message"] = tr(language, "peat_criterion_scope")
        coverage.append(excluded)
    source_metadata = inputs["source_metadata"]
    water_evidence = retrieved.get("water_evidence", {})
    water_source_ids = (
        "syke_rantaviiva_line_river", "syke_rantaviiva_polygon_river", "syke_rantaviiva_lake",
    )
    water_retrieval = {
        row["service_id"]: {
            key: row.get(key)
            for key in ("endpoint", "feature_type", "source_crs", "provider", "spatial_filter",
                        "request_bbox", "request_bbox_crs",
                        "query_time", "schema_discovered_at", "provider_fields", "schema",
                        "buffer_distance_m", "geometry_policy", "query_extent_expansion_m",
                        "source_retrieved_feature_count", "derived_buffer_feature_count", "buffers_generated_count")
        }
        for row in retrieved["coverage"] if row.get("service_id") in water_source_ids
    }
    for source_id in water_source_ids:
        if source_id in water_retrieval:
            water_retrieval[source_id]["provider_fields"] = list(
                source_metadata[source_id].get("provider_fields", ())
            )
    has_water_geometry = (
        water_evidence.get("geometry") is not None
        and not water_evidence["geometry"].isNull()
        and not water_evidence["geometry"].isEmpty()
    )
    coverage.append({
        "service_id": "derived_riparian_buffer_evidence",
        "status": "AVAILABLE",
        "scope": "derived_sensitivity_evidence",
        "derived_from_source_ids": water_source_ids,
        "source_refs": water_evidence.get("source_refs", ()),
        "source_update_dates": water_evidence.get("source_update_dates", ()),
        "source_retrieved_feature_count": water_evidence.get("source_retrieved_feature_count", 0),
        "buffers_generated_count": water_evidence.get("buffers_generated_count", 0),
        "aoi_contributing_buffer_feature_count": water_evidence.get("aoi_contributing_buffer_feature_count", 0),
        "evidence_feature_count": water_evidence.get("evidence_feature_count", 0),
        "combined_output_feature_count": 1 if has_water_geometry else 0,
        "buffer_distance_m": water_evidence.get("buffer_distance_m", 30.0),
        "buffer_distance_units": "metres",
        "criterion_minimum_overlap_m2": 1.0,
        "criterion_comparison": "strictly_greater_than",
        "geometry_policy": "union_of_individual_buffers_clipped_to_aoi",
        "source_retrieval": water_retrieval,
        "message": tr(language, "water_buffer_provenance"),
    })
    stand_fields = source_metadata["forest_centre_stand"]["provider_fields"]
    confirmed_stand_fields = sorted({
        name for name in stand_fields
        if name.lower() in STAND_SCHEMA_FIELD_CANDIDATES
    })
    retained_stand_metrics = {*STAND_VOLUME_FIELDS, "growth_percent", "basal_area_m2_ha", "stumpage_price_eur_m3", "sawlog_value_eur"}
    mapped_metrics = sorted((set(mapped_metric_ids(confirmed_stand_fields)) & retained_stand_metrics)
                            | {"stumpage_price_eur_m3", "sawlog_value_eur"})
    coverage.append({
        "service_id": "forest_centre_stand_indicators",
        "status": "AVAILABLE",
        "mapped_metrics": mapped_metrics,
        "unavailable_metrics": sorted(retained_stand_metrics - set(mapped_metrics)),
        "schema_confirmed_fields": confirmed_stand_fields,
        "mapping_status": "PARTIALLY_MAPPED",
        "message": tr(language, "stand_indicators_mapping"),
    })
    stand_coverage = next((row for row in coverage if row["service_id"] == "forest_centre_stand"), {})
    stand_coverage["stand_feature_count"] = len(
        retrieved["source_features"]["forest_centre_stand"]
    )
    limitations = [
        tr(language, "prototype_notice"),
        tr(language, "limit_overlap"),
        tr(language, "limit_mapping"),
        tr(language, "limit_sensitivity"),
        tr(language, "limit_scope"),
        tr(language, "note_area_definitions"),
        tr(language, "note_grid_weighting"),
        tr(language, "note_volume_comparison"),
        tr(language, "note_result_precision"),
        tr(language, "note_reporting_domain"),
        tr(language, "note_age_rounding"),
        tr(language, "note_partial_values"),
        tr(language, "note_source_dates"),
        tr(language, "note_deferred_metrics"),
        tr(language, "note_sawlog_value"),
        tr(language, "note_water_buffer"),
    ]
    grid_fields = {
        name.lower(): name for name in source_metadata["forest_centre_gridcell"]["provider_fields"]
    }
    source_dates = {}
    for canonical in ("treedatadate", "updatetime"):
        actual = grid_fields.get(canonical)
        observed = set()
        for record in retrieved["source_features"].get("forest_centre_gridcell", ()):
            attributes = {str(key).lower(): value for key, value in record.get("attributes", {}).items()}
            value = attributes.get(canonical)
            if not QgsVariantUtils.isNull(value):
                observed.add(str(value) if isinstance(value, str) else json_default(value))
        source_dates[canonical] = {"provider_field": actual, "observed_values": sorted(observed)}
    run_metadata = [{
        "project_name": tr(language, "project_name"),
        "project_status": "personal_learning_prototype",
        "prototype_notice": tr(language, "prototype_notice"),
        "run_id": run_id,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "language": language,
        "analysis_crs": "EPSG:3067",
        "aoi_crs": inputs["aoi_crs"],
        "result_feature_count": len(classified["result_rows"]),
        "skipped_stand_count": classified.get("result_geometry_filter", {}).get("excluded_stand_count", 0),
        "stand_overlap_summary": classified["stand_overlap_summary"],
        "result_geometry_filter": classified.get("result_geometry_filter", {}),
        "sources": source_metadata,
        "data_attribution": data_attribution(
            inputs["service_ids"], tr(language, "data_attribution_changes"),
        ),
        "grid_source_dates": source_dates,
        "classification_semantics": {
            "potential_protected_age": {
                "source_id": "forest_centre_stand", "field": "MEANAGE", "unit": "years",
                "rule": "MEANAGE > 80", "tiers": ["protection", "superprotection"],
                "scope": "all pieces of the parent stand",
                "unknown": "missing, nonnumeric, boolean, nonfinite or negative age",
                "interpretation": "potential protection based on age; not legal protection",
            },
            "potential_protected_peatland": {
                "source_id": "forest_centre_stand", "field": "SOILTYPE", "unit": "soil code",
                "rule": "60 <= SOILTYPE <= 69 and SOILTYPE is integral",
                "tiers": ["balance", "protection", "superprotection"],
                "scope": "all pieces of the parent stand",
                "unknown": "missing, nonnumeric, boolean, nonfinite, fractional or unrecognized soil code",
                "interpretation": "potential protection based on stand soil code; not legal protection",
            },
            "riparian_buffer": {
                "source_ids": water_source_ids,
                "tiers": ["balance", "protection", "superprotection"],
                "minimum_piece_overlap_m2": 1.0,
                "comparison": "strictly greater than",
                "scope": "individual classified result piece; no parent-stand promotion",
            },
        },
        "water_buffer_evidence": {
            "source_ids": water_source_ids,
            "source_refs": water_evidence.get("source_refs", ()),
            "source_update_dates": water_evidence.get("source_update_dates", ()),
            "buffer_distance_m": water_evidence.get("buffer_distance_m", 30.0),
            "buffer_distance_units": "metres",
            "criterion_minimum_overlap_m2": 1.0,
            "criterion_comparison": "strictly_greater_than",
            "geometry_policy": "buffer_in_epsg_3067_then_union_and_clip_to_aoi",
            "polygon_buffer_includes_source_geometry": True,
            "line_buffer": "two_sided_30_m",
            "source_retrieved_feature_count": water_evidence.get("source_retrieved_feature_count", 0),
            "buffers_generated_count": water_evidence.get("buffers_generated_count", 0),
            "aoi_contributing_buffer_feature_count": water_evidence.get("aoi_contributing_buffer_feature_count", 0),
            "evidence_feature_count": water_evidence.get("evidence_feature_count", 0),
            "combined_output_feature_count": 1 if has_water_geometry else 0,
            "source_retrieval": water_retrieval,
            "attribution": data_attribution(water_source_ids, tr(language, "data_attribution_changes")),
        },
        "metric_coverage": summarize_indicator_rows(classified["result_rows"])["indicator_coverage"],
        "indicator_semantics": {
            "result_field_rounding": {"decimals": RESULT_DECIMALS, "mode": "ROUND_HALF_UP", "stage": "after_aggregation"},
            "reporting_domain": "classified_forest_polygons",
            "area_method": "EPSG:3067 planar intersection m2 / 10000",
            "area_arithmetic": {
                "coordinate_frame": "translated_EPSG:3067",
                "closure_bound": "max(1e-8 m2, 8 * coordinate_ulp_m * polygon_perimeter_m)",
            },
            "grid_density": "sum(intersected_ha * value) / sum(metric_valid_ha)",
            "stand_density": "sum(result_piece_ha * stand_value) / sum(metric_valid_ha)",
            "stand_growth_percent": "100 * stand.volumegrowth / stand.volume; area-weighted mean of valid stand rates",
            "age_bands": {"share_under_20": "AGE < 20", "share_20_80": "20 <= AGE <= 80", "share_over_80": "AGE > 80"},
            "age_share": "100 * sum(matching_ha) / sum(valid_age_ha); final whole percent ROUND_HALF_UP",
            "area_totals": "sum(matching_ha) only if all reporting area known; otherwise null with observed lower bound",
            "grid_metrics": [*GRID_VOLUME_FIELDS, *AGE_METRICS, *AREA_METRICS],
            "stand_metrics": sorted(retained_stand_metrics),
            "stumpage_price_eur_m3": {
                "origin": "USER_SUPPLIED", "input_eur_m3": inputs["sawlog_price_eur_m3"],
                "applies_to": "positive_finite_stand_sawlogvolume_only",
                "group_mean": "sum(unrounded_represented_sawlog_m3 * price) / sum(unrounded_represented_sawlog_m3)",
                "excludes": ["pulpwood_price", "all_standing_timber_price", "whole_forest_value"],
            },
            "sawlog_value_eur": {
                "formula": "unrounded_piece_hectares * stand.sawlogvolume * user_supplied_sawlog_price_eur_m3",
                "unit": "EUR", "source": "forest_centre_stand.sawlogvolume",
                "group_total": "sum(unrounded_known_euros) only if complete; otherwise null with known weighted_sum subtotal",
                "known_zero": "zero sawlogvolume gives zero euros",
                "excludes": ["pulpwood_value", "whole_forest_value", "scenario_income"],
            },
        },
        "parameters": {
            "aoi_layer": inputs["aoi_name"],
            "selected_features_only": inputs["selected_only"],
            "source_ids": list(inputs["service_ids"]),
            "output_name": inputs["base_name"],
            "sawlog_price_eur_m3": inputs["sawlog_price_eur_m3"],
            "sawlog_price_origin": "USER_SUPPLIED",
            "sawlog_price_source": "forest_centre_stand.sawlogvolume",
            "sawlog_price_weight": "unrounded_piece_hectares_times_sawlog_m3_per_hectare",
        },
        "limitations": limitations,
    }]
    return {
        "coverage": coverage,
        "snapshots": [*retrieved["snapshots"], ("buffered_water_evidence", create_water_evidence_layer(water_evidence, language))],
        "limitations": limitations,
        "run_metadata": run_metadata,
    }


def write_outputs(inputs, retrieved, classified, publication, feedback=None):
    """Write the two formats as one attempt and remove partial outputs on failure."""
    language = inputs["language"]
    gpkg_path = inputs["gpkg_path"]
    xlsx_path = inputs["xlsx_path"]
    result_rows = classified["result_rows"]
    coverage = publication["coverage"]
    limitations = publication["limitations"]
    run_metadata = publication["run_metadata"]
    run_id = run_metadata[0]["run_id"]
    current_step = "geopackage"

    try:
        _check_cancelled(feedback, language)
        _feedback(feedback, "setProgress", 91)
        _feedback(feedback, "setProgressText", tr(language, "progress_write_geopackage"))
        _feedback(feedback, "pushInfo", tr(language, "progress_write_geopackage"))
        step_started = time.perf_counter()
        logger.info("run_id=%s stage=output_writing step=geopackage started", run_id)
        write_geopackage(
            gpkg_path, classified["output_layer"], publication["snapshots"], coverage,
            run_metadata, inputs["transform_context"],
        )
        logger.info(
            "run_id=%s stage=output_writing step=geopackage completed elapsed_seconds=%.3f",
            run_id, time.perf_counter() - step_started,
        )
        _check_cancelled(feedback, language)
        _feedback(feedback, "setProgress", 94)
        current_step = "summaries"
        _feedback(feedback, "setProgressText", tr(language, "progress_summarize"))
        _feedback(feedback, "pushInfo", tr(language, "progress_summarize"))
        step_started = time.perf_counter()
        logger.info("run_id=%s stage=output_writing step=summaries started", run_id)
        tier_rows = []
        class_labels = {
            "SENSITIVE": tr(language, "class_sensitive"),
            "ECONOMIC": tr(language, "class_economic"),
            "UNKNOWN": tr(language, "class_unknown"),
        }
        for tier, _label in TIERS:
            for class_code in ("SENSITIVE", "ECONOMIC", "UNKNOWN"):
                members = [row for row in result_rows if row["classes"][tier] == class_code]
                aggregate_rows = [
                    {"class": class_code, "area_ha": row["area_ha"],
                     "indicator_coverage": row["indicator_coverage"]}
                    for row in members
                ]
                summary = weighted_summary(aggregate_rows, class_code)
                summary.update({
                    "tier": tr(language, "tier_" + tier),
                    "class": class_labels[class_code],
                })
                tier_rows.append(summary)
        logger.info(
            "run_id=%s stage=output_writing step=summaries completed summary_count=%d elapsed_seconds=%.3f",
            run_id, len(tier_rows), time.perf_counter() - step_started,
        )
        _feedback(feedback, "setProgress", 96)
        current_step = "workbook"
        _feedback(feedback, "setProgressText", tr(language, "progress_write_workbook"))
        _feedback(feedback, "pushInfo", tr(language, "progress_write_workbook"))
        step_started = time.perf_counter()
        logger.info("run_id=%s stage=output_writing step=workbook started", run_id)
        write_workbook(xlsx_path, language, tier_rows, coverage, limitations, run_metadata)
        logger.info(
            "run_id=%s stage=output_writing step=workbook completed elapsed_seconds=%.3f",
            run_id, time.perf_counter() - step_started,
        )
        _check_cancelled(feedback, language)
    except Exception as exc:
        logger.exception(
            "run_id=%s stage=output_writing step=%s failed",
            run_id, current_step,
        )
        # One file may already be complete when the other fails; remove both so
        # neither can be mistaken for a complete run.
        for path in (gpkg_path, xlsx_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        if feedback is not None and feedback.isCanceled():
            raise QgsProcessingException(tr(language, "error_cancelled"))
        raise QgsProcessingException(tr(language, "error_write", detail=exc))

    _feedback(feedback, "setProgress", 100)
    return {
        "result_layer": classified["output_layer"],
        "gpkg_path": gpkg_path,
        "xlsx_path": xlsx_path,
        "coverage": coverage,
        "run_metadata": run_metadata[0],
        "language": language,
    }
