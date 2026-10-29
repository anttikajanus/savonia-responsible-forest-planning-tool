"""Required explicit sawlog price at the shared Processing boundary."""
import json
from pathlib import Path
import unittest
from qgis_test_environment import qgis_application
APP = qgis_application()
from qgis.core import QgsProcessingException, QgsVectorLayer, QgsVariantUtils
from workflow_fixture import WorkflowFixtureMixin, coordinates, fixture_sources, source_record
from test_grid_publication import workbook_rows
from savonia_responsible_forest_planning_tool.i18n import tr

class SawlogPriceWorkflowTest(WorkflowFixtureMixin, unittest.TestCase):
    def test_calculated_value_is_published_in_both_languages_with_partial_totals_explicit(self):
        fields = fixture_sources()
        stands = [source_record({**fields["forest_centre_stand"], "standid": str(index),
                                  "SAWLOGVOLUME": volume}, x=350000 + 100 * index)
                  for index, volume in enumerate((506.26885023593775, 0, None))]
        for language in ("fi", "en"):
            with self.subTest(language=language), self.scenario([], stands,
                    aoi=[coordinates(350000, 6900000, 300, 100)]) as (fixture, layers, aoi):
                fixture.records["syke_groundwater_areas"] = [source_record(
                    fields["syke_groundwater_areas"], width=200)]
                result = self.run_algorithm(layers, aoi, language, "value-" + language, sawlog_price=10)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                features = {feature["source_stand_id"]: feature for feature in layer.getFeatures()}
                value_index = layer.fields().indexFromName("sawlog_value_eur")
                self.assertGreaterEqual(value_index, 0)
                self.assertEqual(value_index, layer.fields().indexFromName("stumpage_price_eur_m3") + 1)
                self.assertEqual(layer.attributeAlias(value_index), "Tukkipuun laskennallinen arvo (€)"
                                 if language == "fi" else "Calculated sawlog value (€)")
                self.assertEqual(features["0"]["sawlog_value_eur"], 5062.69)
                self.assertEqual(features["0"]["stumpage_price_eur_m3"], 10)
                self.assertEqual(features["1"]["sawlog_value_eur"], 0)
                self.assertTrue(QgsVariantUtils.isNull(features["2"]["sawlog_value_eur"]))
                statistics = json.loads(features["0"]["indicator_coverage"])["sawlog_value_eur"]
                self.assertAlmostEqual(statistics["weighted_sum"], 5062.688502359378)
                sheets = workbook_rows(result["EXCEL"])
                summary = sheets[tr(language, "sheet_summary")]
                value_column = summary[0].index(layer.attributeAlias(value_index))
                complete = next(row for row in summary if row[:2] == [tr(language, "tier_balance"), tr(language, "class_sensitive")])
                partial = next(row for row in summary if row[:2] == [tr(language, "tier_all_out"), tr(language, "class_economic")])
                self.assertEqual(complete[value_column], 5062.69)
                self.assertIsNone(partial[value_column])
                metric_rows = sheets[tr(language, "sheet_metric_coverage")]
                header = metric_rows[0]
                metric_id = header.index(tr(language, "column_metric_id"))
                value_coverage = next(row for row in metric_rows[1:] if row[:2] == [tr(language, "tier_all_out"), tr(language, "class_economic")]
                                      and row[metric_id] == "sawlog_value_eur")
                self.assertEqual(value_coverage[header.index(tr(language, "column_status"))], "PARTIAL")
                self.assertAlmostEqual(value_coverage[header.index(tr(language, "column_weighted_sum"))], 5062.688502359378)
                metadata = QgsVectorLayer(result["RESULT"].split("|")[0] + "|layername=run_metadata", "metadata", "ogr")
                record, = list(metadata.getFeatures())
                semantics = json.loads(record["indicator_semantics"])["sawlog_value_eur"]
                self.assertEqual(semantics["unit"], "EUR")
                self.assertIn("stand.sawlogvolume", semantics["formula"])

    def test_invalid_price_rejected_before_feature_requests_and_outputs(self):
        with self.scenario([]) as (fixture, layers, aoi):
            before = list(fixture.requests)
            for price in (None, 0, -1, float("nan"), float("inf"), 1.234):
                for language in ("fi", "en"):
                    with self.subTest(price=price, language=language):
                        with self.assertRaises(QgsProcessingException):
                            self.run_algorithm(layers, aoi, language, "invalid-price", sawlog_price=price)
                        self.assertEqual(list(Path(self.temp.name).glob("*.gpkg")), [])
                        self.assertEqual(list(Path(self.temp.name).glob("*.xlsx")), [])
            self.assertEqual(fixture.requests, before)

    def test_price_published_with_source_volume_coverage_and_durable_origin(self):
        fields = fixture_sources()["forest_centre_stand"]
        stands = [source_record({**fields, "standid": "positive", "SAWLOGVOLUME": 0.000001})]
        for language in ("en", "fi"):
            with self.subTest(language=language), self.scenario([], stands) as (_, layers, aoi):
                result = self.run_algorithm(layers, aoi, language, "price-" + language)
                layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
                feature, = list(layer.getFeatures())
                self.assertEqual(feature["stumpage_price_eur_m3"], 75.25)
                self.assertEqual(feature["sawtimber_volume_m3_ha"], 0)
                self.assertEqual(layer.attributeAlias(layer.fields().indexFromName("stumpage_price_eur_m3")),
                                 tr(language, "metric_stumpage_price_eur_m3"))
                coverage = json.loads(feature["indicator_coverage"])["stumpage_price_eur_m3"]
                self.assertEqual(coverage["represented_volume_m3"], 0.000001)
                self.assertEqual(coverage["status"], "AVAILABLE")
                metadata = QgsVectorLayer(result["RESULT"].split("|")[0] + "|layername=run_metadata", "metadata", "ogr")
                record, = list(metadata.getFeatures())
                parameters = json.loads(record["parameters"])
                self.assertEqual(parameters["sawlog_price_eur_m3"], 75.25)
                self.assertEqual(parameters["sawlog_price_origin"], "USER_SUPPLIED")
                sheets = workbook_rows(result["EXCEL"])
                summary = sheets[tr(language, "sheet_summary")]
                index = summary[0].index(tr(language, "metric_stumpage_price_eur_m3"))
                self.assertTrue(any(row[index] == 75.25 for row in summary[1:]))

    def test_single_price_is_constant_for_unequal_sawlogs_and_null_for_ineligible_stands(self):
        fields = fixture_sources()["forest_centre_stand"]
        volumes = (100, 300, 0, None, -1)
        stands = [source_record({**fields, "standid": str(index), "SAWLOGVOLUME": volume},
                                x=350000 + 100 * index)
                  for index, volume in enumerate(volumes)]
        with self.scenario([], stands, aoi=[coordinates(350000, 6900000, 500, 100)]) as (_, layers, aoi):
            result = self.run_algorithm(layers, aoi, "en", "unequal-sawlogs", sawlog_price=83.65)
            layer = QgsVectorLayer(result["RESULT"], "result", "ogr")
            features = {feature["source_stand_id"]: feature for feature in layer.getFeatures()}
            for index in range(5):
                price = features[str(index)]["stumpage_price_eur_m3"]
                if index < 2:
                    self.assertEqual(price, 83.65)
                else:
                    self.assertTrue(QgsVariantUtils.isNull(price))
            sheets = workbook_rows(result["EXCEL"])
            coverage = sheets[tr("en", "sheet_metric_coverage")]
            header = coverage[0]
            matching = [row for row in coverage[1:] if row[header.index(tr("en", "column_metric_id"))] == "stumpage_price_eur_m3"
                        and row[header.index(tr("en", "column_represented_volume"))] == 400]
            self.assertTrue(matching)
            self.assertEqual(matching[0][header.index(tr("en", "column_weighted_sum"))], 33460)
