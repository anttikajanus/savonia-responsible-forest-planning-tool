"""Artifact contracts for grid/stand indicators, using generated local data."""

import json
import posixpath
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


from qgis_test_environment import qgis_application

APP = qgis_application()

from qgis.core import NULL, QgsApplication, QgsCoordinateTransformContext, QgsGeometry, QgsVectorLayer


from savonia_responsible_forest_planning_tool.analysis.classification import assemble_classified_piece
from savonia_responsible_forest_planning_tool.adapters.classified_result import create_classified_result_layer
from savonia_responsible_forest_planning_tool.adapters.geopackage_writer import write_geopackage
from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.analysis.classification import TIERS
from savonia_responsible_forest_planning_tool.analysis.workflow_steps.publishing import prepare_publication, write_outputs
from savonia_responsible_forest_planning_tool.i18n import tr


def classified_row(grid_area=0.625, grid_volume=250, stand_volume=200, age=19):
    row = assemble_classified_piece("stand-1", {"volume": stand_volume, "sawlogvolume": 80,
        "volumegrowth": 4, "basalarea": 20}, 1, {}, {"forest_centre_stand": "AVAILABLE"},
        [{"area_ha": grid_area, "source_id": "cell-1", "values": {
            "volume": grid_volume, "volumepine": 100, "volumespruce": 80,
            "volumedeciduous": 70, "age": age, "soiltype": 60, "drainagestate": 6}}])
    row["geometry"] = QgsGeometry.fromWkt("POLYGON ((350000 6900000,350100 6900000,350100 6900100,350000 6900100,350000 6900000))")
    return row


def workbook_rows(path):
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    package_relationship = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    office_relationship = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        root_relationships = ET.fromstring(archive.read("_rels/.rels"))
        workbooks = [relationship for relationship in root_relationships.findall(package_relationship)
                     if relationship.attrib["Type"] == office_relationship + "/officeDocument"]
        if len(workbooks) != 1:
            raise ValueError("XLSX package must contain one Office document workbook relationship")
        workbook_path = workbooks[0].attrib["Target"].lstrip("/")
        workbook_folder, workbook_name = posixpath.split(workbook_path)
        relationships_path = posixpath.join(workbook_folder, "_rels", workbook_name + ".rels")
        workbook_relationships = ET.fromstring(archive.read(relationships_path))
        sheet_targets = {relationship.attrib["Id"]: relationship.attrib["Target"]
                         for relationship in workbook_relationships.findall(package_relationship)
                         if relationship.attrib["Type"] == office_relationship + "/worksheet"}
        sheets = ET.fromstring(archive.read(workbook_path)).find("s:sheets", ns)
        result = {}
        for sheet in sheets:
            target = sheet_targets[sheet.attrib["{" + office_relationship + "}id"]]
            sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(workbook_folder, target))
            document = ET.fromstring(archive.read(sheet_path))
            rows = []
            for row in document.findall("s:sheetData/s:row", ns):
                values = []
                for cell in row:
                    numeric = cell.find("s:v", ns)
                    text = cell.find("s:is/s:t", ns)
                    values.append(float(numeric.text) if numeric is not None else text.text if text is not None else None)
                rows.append(values)
            result[sheet.attrib["name"]] = rows
        return result


class GridPublicationTests(unittest.TestCase):
    def test_reopened_geopackage_preserves_integer_ages_aliases_and_exact_coverage(self):
        for language, grid_label, stand_label in (
            ("en", "Grid total volume (m³/ha)", "Stand total volume (m³/ha)"),
            ("fi", "Hila kokonaistilavuus (m³/ha)", "Kuvio kokonaistilavuus (m³/ha)"),
        ):
            with self.subTest(language=language), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
                row = classified_row()
                # Large coverage payloads must not be silently truncated.
                row["indicator_coverage"]["audit"] = {"original": "x" * 12000}
                layer = create_classified_result_layer([row], language)
                path = str(Path(folder) / "indicators.gpkg")
                write_geopackage(path, layer, [], [{"service_id": "fixture", "status": "AVAILABLE"}],
                    [{"run_id": "test", "large_payload": "y" * 12000}], QgsCoordinateTransformContext())
                reopened = QgsVectorLayer(path + "|layername=classified_forest_polygons", "result", "ogr")
                iterator = reopened.getFeatures()
                feature = next(iterator)
                iterator.close()
                try:
                    self.assertTrue(reopened.isValid())
                    self.assertEqual(feature["grid_total_volume_m3_ha"], 250)
                    self.assertEqual(feature["total_volume_m3_ha"], 200)
                    self.assertEqual(feature["deciduous_volume_m3_ha"], 70)
                    self.assertEqual(feature["share_under_20"], 100)
                    self.assertIn(reopened.fields().field("share_under_20").typeName().lower(), ("integer", "integer64"))
                    self.assertEqual(reopened.attributeAlias(reopened.fields().indexFromName("grid_total_volume_m3_ha")), grid_label)
                    self.assertEqual(reopened.attributeAlias(reopened.fields().indexFromName("total_volume_m3_ha")), stand_label)
                    coverage = json.loads(feature["indicator_coverage"])
                    self.assertEqual(coverage, row["indicator_coverage"])
                    self.assertEqual(coverage["share_under_20"]["coverage_percent"], 63)
                    self.assertEqual(coverage["share_under_20"]["coverage_percent_exact"], 62.5)
                    self.assertNotIn("indicator_status", reopened.fields().names())
                    self.assertNotIn("indicator_diagnostics", reopened.fields().names())
                    statuses = {metric: item["status"] for metric, item in json.loads(feature["indicator_coverage"]).items() if "status" in item}
                    self.assertNotIn("birch_volume_m3_ha", statuses)
                    self.assertNotIn("birch_volume_m3_ha", coverage)
                    self.assertNotIn("birch_volume_m3_ha", reopened.fields().names())
                    self.assertEqual(statuses["stumpage_price_eur_m3"], "UNKNOWN_FIELD_OR_VALUE")
                finally:
                    del feature, iterator, reopened, layer
                metadata = QgsVectorLayer(path + "|layername=run_metadata", "metadata", "ogr")
                try:
                    self.assertEqual(next(metadata.getFeatures())["large_payload"], "y" * 12000)
                finally:
                    del metadata

    def test_shared_publisher_exports_sufficient_statistic_summaries_and_metric_coverage(self):
        water_source_types = {
            "syke_rantaviiva_line_river": "syke_rantaviiva:Ranta10_Viivamainen_joki",
            "syke_rantaviiva_polygon_river": "syke_rantaviiva:Ranta10_Aluemainen_joki",
            "syke_rantaviiva_lake": "syke_rantaviiva:Ranta10_Jarvi",
        }
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                rows = [classified_row(0.25, 100, 100, 19), classified_row(1, 300, 300, 81)]
                for row in rows:
                    row["classes"] = {tier: "ECONOMIC" for tier, _ in TIERS}
                inputs = {"language": language, "output_folder": folder, "base_name": "test",
                          "sawlog_price_eur_m3": 75.25,
                    "gpkg_path": str(Path(folder) / "test.gpkg"), "xlsx_path": str(Path(folder) / "test.xlsx"),
                    "transform_context": QgsCoordinateTransformContext(), "aoi_crs": "EPSG:3067",
                    "aoi_name": "AOI", "selected_only": False,
                    "service_ids": ["forest_centre_stand", "forest_centre_gridcell"],
                    "source_metadata": {
                        "forest_centre_stand": {"provider_fields": ["VOLUME", "SAWLOGVOLUME", "VOLUMEGROWTH", "BASALAREA", "MEANAGE", "PROPORTIONPINE"]},
                        "forest_centre_gridcell": {"provider_fields": ["VOLUME", "AGE", "TREEDATADATE", "UPDATETIME"]}}}
                inputs["source_metadata"].update({
                    source_id: {"provider_fields": ["objectid", "muutospvm"]}
                    for source_id in water_source_types
                })
                retrieved = {"source_features": {"forest_centre_stand": [{}, {}], "forest_centre_gridcell": [
                    {"attributes": {"TREEDATADATE": "2020-06-01", "UPDATETIME": "2026-10-25"}},
                    {"attributes": {"TREEDATADATE": NULL, "UPDATETIME": NULL}}]}, "snapshots": [],
                    "coverage": [
                        {"service_id": source_id, "feature_type": feature_type,
                         "endpoint": "https://example.invalid/wfs", "source_crs": "EPSG:3067",
                         "provider": "WFS", "spatial_filter": "expanded_bbox"}
                        for source_id, feature_type in water_source_types.items()
                    ]}
                classified = {"result_rows": rows, "output_layer": create_classified_result_layer(rows, language),
                    "stand_overlap_summary": {"pair_count": 0, "affected_stand_count": 0, "stand_id_sample": []},
                    "coverage": [{"service_id": "forest_centre_stand", "status": "AVAILABLE"}]}
                publication = prepare_publication(inputs, retrieved, classified, "grid-test")
                water_retrieval = publication["run_metadata"][0]["water_buffer_evidence"]["source_retrieval"]
                self.assertEqual(
                    {source_id: row["feature_type"] for source_id, row in water_retrieval.items()},
                    water_source_types,
                )
                self.assertTrue(all(row["provider_fields"] == ["objectid", "muutospvm"]
                                    for row in water_retrieval.values()))
                self.assertEqual(publication["run_metadata"][0]["grid_source_dates"]["treedatadate"]["observed_values"], ["2020-06-01"])
                self.assertEqual(publication["run_metadata"][0]["metric_coverage"]["grid_total_volume_m3_ha"]["valid_area_ha"], 1.25)
                peat_criterion = next(item for item in publication["coverage"] if item["service_id"] == "peatlands")
                self.assertEqual(peat_criterion["scope"], "sensitivity_criterion")
                self.assertTrue(peat_criterion["message"])
                stand_mapping = next(item for item in publication["coverage"] if item["service_id"] == "forest_centre_stand_indicators")
                self.assertNotIn("pine_volume_m3_ha", stand_mapping["mapped_metrics"])
                self.assertNotIn("share_under_20", stand_mapping["mapped_metrics"])
                result = write_outputs(inputs, retrieved, classified, publication)
                workbook = workbook_rows(result["xlsx_path"])
                summary = workbook[tr(language, "sheet_summary")]
                headers = summary[0]
                group = next(row for row in summary[1:] if row[headers.index(tr(language, "column_features"))] == 2)
                value = lambda metric: group[headers.index(tr(language, "metric_" + metric))]
                self.assertEqual(value("grid_total_volume_m3_ha"), 260)
                self.assertEqual(value("total_volume_m3_ha"), 200)
                self.assertEqual([value(metric) for metric in ("share_under_20", "share_20_80", "share_over_80")], [20, 0, 80])
                self.assertIsNone(value("peatland_area_ha"))
                self.assertNotIn("birch_volume_m3_ha", publication["run_metadata"][0]["indicator_semantics"])
                self.assertIsNone(value("stumpage_price_eur_m3"))
                coverage = workbook[tr(language, "sheet_metric_coverage")]
                header = coverage[0]
                metric_col = header.index(tr(language, "column_metric_id"))
                peat = next(row for row in coverage[1:] if row[metric_col] == "peatland_area_ha" and row[header.index(tr(language, "column_unknown_area"))] == 0.75)
                self.assertEqual(peat[header.index(tr(language, "column_matching_area"))], 1.25)
                age = next(row for row in coverage[1:] if row[metric_col] == "share_under_20" and row[header.index(tr(language, "column_unknown_area"))] == 0.75)
                self.assertEqual(age[header.index(tr(language, "column_age_coverage"))], 63)
                self.assertIn("2020-06-01", str(workbook[tr(language, "sheet_notes")]))
                self.assertEqual(publication["run_metadata"][0]["indicator_semantics"]["reporting_domain"], "classified_forest_polygons")

    def test_large_metadata_remains_complete_within_excel_text_cell_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "large.xlsx")
            payload = "measurements-" * 4000
            write_workbook(path, "en", [], [{"service_id": "grid", "status": "AVAILABLE", "schema": payload}], [],
                [{"run_id": "test", "large_payload": payload}])
            workbook = workbook_rows(path)
            for rows in workbook.values():
                self.assertTrue(all(len(cell) <= 32767 for row in rows for cell in row if isinstance(cell, str)))
            fragments = [row[2] for row in workbook["Notes"] if row and row[0] == "large_payload"]
            self.assertEqual("".join(fragments), payload)
            source_fragments = [row[2] for row in workbook["Source coverage"][1:]]
            self.assertEqual(json.loads("".join(source_fragments))["schema"], payload)


if __name__ == "__main__":
    unittest.main()
