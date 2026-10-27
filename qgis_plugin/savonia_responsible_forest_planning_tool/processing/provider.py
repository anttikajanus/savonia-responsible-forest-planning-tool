"""Processing Toolbox entry point over the shared application workflow."""

import logging

from qgis.core import (
    Qgis, QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterBoolean, QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString, QgsProcessingParameterVectorLayer,
    QgsProcessingOutputFile, QgsProcessingOutputVectorLayer,
    QgsProcessingProvider, QgsMessageLog,
)

from ..i18n import selected_language, tr
from ..documentation import ResourceError, manual_url
from ..app_logging import LOGGER_NAME, PLUGIN_TAG
from ..analysis.workflow import run_workflow


class ResponsibleForestPlanningInputsAlgorithm(QgsProcessingAlgorithm):
    AOI = "AOI"
    SELECTED_ONLY = "SELECTED_ONLY"
    STANDS = "STANDS"
    GRIDCELLS = "GRIDCELLS"
    HABITATS = "HABITATS"
    PROTECTED = "PROTECTED"
    PROTECTED_PRIVATE = "PROTECTED_PRIVATE"
    PROTECTED_WILDERNESS = "PROTECTED_WILDERNESS"
    PROGRAMME = "PROGRAMME"
    GROUNDWATER = "GROUNDWATER"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    OUTPUT_NAME = "OUTPUT_NAME"
    RESULT = "RESULT"
    EXCEL = "EXCEL"

    def name(self):
        return "prepare_forest_scenario_inputs"

    def displayName(self):
        return tr(selected_language(), "algorithm_name")

    def group(self):
        return tr(selected_language(), "algorithm_group")

    def groupId(self):
        return "savonia_forest_planning"

    def shortHelpString(self):
        language = selected_language()
        return tr(language, "prototype_notice") + "\n\n" + tr(language, "algorithm_help")

    def helpUrl(self):
        language = selected_language()
        try:
            return manual_url(language, "processing")
        except ResourceError:
            logging.getLogger(LOGGER_NAME + ".processing").exception(
                "stage=documentation error_code=HELP_RESOURCE_UNAVAILABLE entry_point=processing")
            QgsMessageLog.logMessage(tr(language, "processing_help_unavailable"), PLUGIN_TAG,
                                     Qgis.MessageLevel.Warning, notifyUser=True)
            return ""

    def createInstance(self):
        return ResponsibleForestPlanningInputsAlgorithm()

    def flags(self):
        # Processing exposes live layer objects, so it must stay on the main thread.
        # The wizard can use a worker because it snapshots those objects first.
        return super().flags() | Qgis.ProcessingAlgorithmFlag.NoThreading

    def initAlgorithm(self, config=None):
        language = selected_language()
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.AOI, tr(language, "aoi_parameter"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SELECTED_ONLY, tr(language, "selected_only"), defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.STANDS, tr(language, "stand_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.GRIDCELLS, tr(language, "gridcell_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.HABITATS, tr(language, "habitat_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.PROTECTED, tr(language, "protected_state_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.PROTECTED_PRIVATE, tr(language, "protected_private_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.PROTECTED_WILDERNESS, tr(language, "protected_wilderness_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.PROGRAMME, tr(language, "programme_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.GROUNDWATER, tr(language, "groundwater_layer"), types=[QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_FOLDER, tr(language, "output_folder")
        ))
        self.addParameter(QgsProcessingParameterString(
            self.OUTPUT_NAME, tr(language, "output_name"), defaultValue="", optional=True
        ))
        self.addOutput(QgsProcessingOutputVectorLayer(self.RESULT, tr(language, "classified_result")))
        self.addOutput(QgsProcessingOutputFile(self.EXCEL, tr(language, "workbook_output")))

    def processAlgorithm(self, parameters, context, feedback):
        sources = {
            "forest_centre_stand": self.parameterAsVectorLayer(parameters, self.STANDS, context),
            "forest_centre_gridcell": self.parameterAsVectorLayer(parameters, self.GRIDCELLS, context),
            "forest_centre_habitat": self.parameterAsVectorLayer(parameters, self.HABITATS, context),
            "syke_protected_areas_state_owned": self.parameterAsVectorLayer(parameters, self.PROTECTED, context),
            "syke_protected_areas_private_land": self.parameterAsVectorLayer(parameters, self.PROTECTED_PRIVATE, context),
            "syke_protected_areas_wilderness": self.parameterAsVectorLayer(parameters, self.PROTECTED_WILDERNESS, context),
            "syke_nature_conservation_programme_areas": self.parameterAsVectorLayer(parameters, self.PROGRAMME, context),
            "syke_groundwater_areas": self.parameterAsVectorLayer(parameters, self.GROUNDWATER, context),
        }
        args = {
            # Pass transforms explicitly so shared workflow code never depends on
            # mutable global QgsProject state.
            "transform_context": context.transformContext(),
            "language": selected_language(),
            "aoi_layer": self.parameterAsVectorLayer(parameters, self.AOI, context),
            "selected_only": self.parameterAsBool(parameters, self.SELECTED_ONLY, context),
            "sources": sources,
            "output_folder": self.parameterAsString(parameters, self.OUTPUT_FOLDER, context),
            "output_name": self.parameterAsString(parameters, self.OUTPUT_NAME, context).strip() or None,
            "entry_point": "processing",
        }
        try:
            result = run_workflow(args, feedback)
        except QgsProcessingException:
            raise
        except Exception as exc:
            raise QgsProcessingException("Forest planning workflow failed: {0}".format(exc))
        return {
            self.RESULT: result["gpkg_path"] + "|layername=classified_forest_polygons",
            self.EXCEL: result["xlsx_path"],
        }


class ResponsibleForestPlanningProcessingProvider(QgsProcessingProvider):
    def id(self):
        return "savonia_forest_planning"

    def name(self):
        return tr(selected_language(), "toolbar_name")

    def longName(self):
        return self.name()

    def loadAlgorithms(self):
        self.addAlgorithm(ResponsibleForestPlanningInputsAlgorithm())
