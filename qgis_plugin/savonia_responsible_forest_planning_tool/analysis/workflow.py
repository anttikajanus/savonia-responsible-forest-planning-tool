"""Shared synchronous workflow orchestration for the wizard and Processing."""

import datetime
import logging
import time
import uuid

from qgis.core import QgsProcessingException

from ..app_logging import LOGGER_NAME, record_business_action
from ..i18n import tr
from .workflow_steps.common import _check_cancelled, _feedback
from .workflow_steps.publishing import prepare_publication, write_outputs
from .workflow_steps.source_loading import retrieve_sources
from .workflow_steps.spatial_classification import classify_source_features
from .workflow_steps.validation import validate_inputs


logger = logging.getLogger(LOGGER_NAME + ".analysis.workflow")


def _run_workflow(parameters, feedback=None):
    """Run the ordered analysis steps using explicit results between phases."""
    language = parameters.get("language", "en")
    run_id = parameters["run_id"]

    parameters["_stage"] = "input_validation"
    logger.info("run_id=%s stage=%s started", run_id, parameters["_stage"])
    stage_started = time.perf_counter()
    _feedback(feedback, "setProgress", 0)
    _feedback(feedback, "setProgressText", tr(language, "progress_validate"))
    _feedback(feedback, "pushInfo", tr(language, "progress_validate"))
    _check_cancelled(feedback, language)
    inputs = validate_inputs(parameters, run_id)
    logger.info(
        "run_id=%s stage=input_validation completed elapsed_seconds=%.3f",
        run_id, time.perf_counter() - stage_started,
    )
    _feedback(feedback, "pushInfo", tr(language, "progress_validate_complete"))
    _feedback(feedback, "setProgress", 10)

    parameters["_stage"] = "source_retrieval"
    logger.info("run_id=%s stage=%s started", run_id, parameters["_stage"])
    stage_started = time.perf_counter()
    retrieved = retrieve_sources(inputs, feedback)
    logger.info(
        "run_id=%s stage=source_retrieval completed source_count=%d total_feature_count=%d elapsed_seconds=%.3f",
        run_id, len(retrieved["coverage"]),
        sum(row["feature_count"] for row in retrieved["coverage"]),
        time.perf_counter() - stage_started,
    )
    _feedback(feedback, "pushInfo", tr(
        language, "progress_sources_complete",
        sources=len(retrieved["coverage"]),
        count=sum(row["feature_count"] for row in retrieved["coverage"]),
    ))

    _feedback(feedback, "pushInfo", tr(language, "progress_overlay"))
    _feedback(feedback, "setProgressText", tr(language, "progress_overlay"))
    parameters["_stage"] = "spatial_classification"
    logger.info("run_id=%s stage=%s started", run_id, parameters["_stage"])
    stage_started = time.perf_counter()
    classified = classify_source_features(inputs, retrieved, feedback)
    logger.info(
        "run_id=%s stage=spatial_classification completed result_feature_count=%d elapsed_seconds=%.3f",
        run_id, len(classified["result_rows"]), time.perf_counter() - stage_started,
    )
    _feedback(feedback, "pushInfo", tr(
        language, "progress_classify_complete", count=len(classified["result_rows"]),
    ))

    parameters["_stage"] = "output_preparation"
    _feedback(feedback, "setProgressText", tr(language, "progress_prepare_outputs"))
    _feedback(feedback, "pushInfo", tr(language, "progress_prepare_outputs"))
    logger.info("run_id=%s stage=%s started", run_id, parameters["_stage"])
    stage_started = time.perf_counter()
    publication = prepare_publication(inputs, retrieved, classified, run_id)
    logger.info(
        "run_id=%s stage=output_preparation completed elapsed_seconds=%.3f",
        run_id, time.perf_counter() - stage_started,
    )
    _check_cancelled(feedback, language)
    _feedback(feedback, "pushInfo", tr(language, "progress_write"))
    _feedback(feedback, "setProgressText", tr(language, "progress_write"))
    _feedback(feedback, "setProgress", 90)
    parameters["_stage"] = "output_writing"
    logger.info("run_id=%s stage=%s started", run_id, parameters["_stage"])
    result = write_outputs(inputs, retrieved, classified, publication, feedback)
    logger.info(
        "run_id=%s stage=%s completed result_feature_count=%d",
        run_id, parameters["_stage"], len(classified["result_rows"]),
    )
    return result


def run_workflow(parameters, feedback=None):
    """Run once with a diagnostic ID and preserve an internal traceback."""
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + "Z-" + uuid.uuid4().hex[:6]
    args = dict(parameters or {})
    args["run_id"] = run_id
    args["_stage"] = "startup"
    available_sources = args.get("sources") or {}
    record_business_action(
        "analysis_run_started",
        run_id=run_id,
        entry_point=args.get("entry_point", "application"),
        selected_features_only=bool(args.get("selected_only", False)),
        configured_source_count=sum(value is not None for value in available_sources.values()),
    )
    logger.info(
        "run_id=%s event=analysis_run_started entry_point=%s configured_source_count=%d",
        run_id, args.get("entry_point", "application"),
        sum(value is not None for value in available_sources.values()),
    )
    try:
        result = _run_workflow(args, feedback)
        record_business_action(
            "analysis_run_completed",
            run_id=run_id,
            entry_point=args.get("entry_point", "application"),
            result_feature_count=result.get("run_metadata", {}).get("result_feature_count"),
        )
        logger.info("run_id=%s event=analysis_run_completed", run_id)
        return result
    except Exception as exc:
        cancelled = feedback is not None and feedback.isCanceled()
        record_business_action(
            "analysis_run_cancelled" if cancelled else "analysis_run_failed",
            run_id=run_id,
            entry_point=args.get("entry_point", "application"),
            stage=args.get("_stage", "unknown"),
            **({} if cancelled else {"error_type": type(exc).__name__}),
        )
        if cancelled:
            logger.info(
                "run_id=%s event=analysis_run_cancelled stage=%s",
                run_id, args.get("_stage", "unknown"),
            )
        else:
            logger.exception(
                "run_id=%s event=analysis_run_failed stage=%s error_type=%s",
                run_id, args.get("_stage", "unknown"), type(exc).__name__,
            )
        raise QgsProcessingException(tr(
            args.get("language", "en"), "error_run", run_id=run_id,
            stage=args.get("_stage", "unknown"), detail=exc,
        ))
