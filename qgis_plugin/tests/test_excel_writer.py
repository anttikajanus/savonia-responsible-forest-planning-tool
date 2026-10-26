"""Excel package relationships must allow readers to discover the workbook."""

from pathlib import Path
import os
import posixpath
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))

from savonia_responsible_forest_planning_tool.adapters.excel_writer import write_workbook
from savonia_responsible_forest_planning_tool.i18n import tr


PACKAGE_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCUMENT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


class ExcelWriterTests(unittest.TestCase):
    def test_workbook_and_localized_sheets_are_discoverable_from_package_root(self):
        for language in ("fi", "en"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "export.xlsx"
                write_workbook(path, language, [], [], ["Export check"])
                with zipfile.ZipFile(path) as archive:
                    self.assertIsNone(archive.testzip())
                    root = ET.fromstring(archive.read("_rels/.rels"))
                    self.assertEqual(root.tag, "{%s}Relationships" % PACKAGE_NS)
                    documents = [
                        relationship for relationship in root
                        if relationship.get("Type") == DOCUMENT_NS + "/officeDocument"
                    ]
                    self.assertEqual(len(documents), 1, "Package must identify its Excel workbook")
                    workbook_path = documents[0].get("Target")
                    workbook = ET.fromstring(archive.read(workbook_path))
                    workbook_folder, workbook_name = posixpath.split(workbook_path)
                    relationships_path = posixpath.join(workbook_folder, "_rels", workbook_name + ".rels")
                    relationships = {
                        relationship.get("Id"): relationship
                        for relationship in ET.fromstring(archive.read(relationships_path))
                    }
                    sheets = workbook.find("{%s}sheets" % SHEET_NS)
                    self.assertEqual([sheet.get("name") for sheet in sheets], [
                        tr(language, key) for key in (
                            "sheet_summary", "sheet_source_coverage", "sheet_metric_coverage", "sheet_notes",
                        )
                    ])
                    for sheet in sheets:
                        relationship = relationships[sheet.get("{%s}id" % DOCUMENT_NS)]
                        self.assertEqual(relationship.get("Type"), DOCUMENT_NS + "/worksheet")
                        target = posixpath.join(workbook_folder, relationship.get("Target"))
                        worksheet = ET.fromstring(archive.read(target))
                        self.assertEqual(worksheet.tag, "{%s}worksheet" % SHEET_NS)
                    for number in (1, 4):
                        worksheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{number}.xml"))
                        values = [node.text for node in worksheet.iter("{%s}t" % SHEET_NS)]
                        self.assertIn(tr(language, "project_name"), values)
                        self.assertIn(tr(language, "prototype_notice"), values)


if __name__ == "__main__":
    unittest.main()
