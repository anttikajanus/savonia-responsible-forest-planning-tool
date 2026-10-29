"""Packaged documentation is usable without importing QGIS or widgets."""

from configparser import ConfigParser
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

sys.path.insert(0, os.environ.get(
    "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
    str(Path(__file__).resolve().parents[1]),
))

from savonia_responsible_forest_planning_tool.documentation import ResourceError, manual_url, metadata, resource_url


class DocumentationTests(unittest.TestCase):
    def test_default_manuals_are_readable_in_checkout_or_installed_package(self):
        for language in ("fi", "en"):
            with self.subTest(language=language):
                parsed = urlsplit(manual_url(language, "processing"))
                path = Path(unquote(parsed.path).lstrip("/") if os.name == "nt" else unquote(parsed.path))
                self.assertEqual(path.name, f"manual_{language}.html")
                self.assertEqual(path.parent.name, "help")
                self.assertIn('id="processing"', path.read_text(encoding="utf-8"))

    def test_unreadable_package_files_raise_resource_errors_with_diagnostic_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "LICENSE").write_bytes(b"\xff")
            with self.assertRaises(ResourceError) as raised:
                resource_url("licence", root)
            self.assertEqual(raised.exception.resource, "licence")
            self.assertEqual(raised.exception.path, str(root / "LICENSE"))
            self.assertEqual(raised.exception.reason, "unreadable")
            self.assertIsInstance(raised.exception.__cause__, UnicodeError)
            with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
                with self.assertRaises(ResourceError) as raised:
                    manual_url("en", package_root=root)
            self.assertEqual(raised.exception.reason, "unreadable")
            self.assertIsInstance(raised.exception.__cause__, PermissionError)

    def test_manual_anchor_must_be_real_and_metadata_must_be_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs" / "help").mkdir(parents=True)
            manual = root / "docs" / "help" / "manual_en.html"
            manual.write_text('<!-- id="workflow" --><a href="#workflow">Start</a>', encoding="utf-8")
            with self.assertRaises(ResourceError) as raised:
                manual_url("en", package_root=root)
            self.assertEqual(raised.exception.reason, "missing_section")
            for text in ("not an ini file", "[other]\nversion=1\n", "[general]\nname=Plugin\nversion=\n"):
                (root / "metadata.txt").write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaises(ResourceError) as raised:
                    metadata(root)
                self.assertEqual(raised.exception.reason, "invalid_metadata")
            (root / "metadata.txt").unlink()
            with self.assertRaises(ResourceError) as raised:
                metadata(root)
            self.assertEqual(raised.exception.reason, "unreadable")

    def test_package_metadata_preserves_version_and_declares_confirmed_identity_and_public_links(self):
        actual = metadata()
        self.assertEqual(actual["name"], "Savonia - Responsible Forest Planning")
        self.assertEqual(actual["name[fi]"], "Savonia - Vastuullinen metsäsuunnittelu")
        package_root = Path(os.environ.get(
            "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
            str(Path(__file__).resolve().parents[1]),
        ))
        expected = ConfigParser(interpolation=None)
        expected.read(package_root / "savonia_responsible_forest_planning_tool" / "metadata.txt", encoding="utf-8")
        self.assertRegex(actual["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(actual["version"], expected["general"]["version"])
        self.assertEqual(actual["author"], "Antti Kajanus")
        self.assertEqual(actual["experimental"], "True")
        self.assertIn("personal learning prototype", actual["description"])
        self.assertIn("not backed or approved by Savonia", actual["description"])
        self.assertIn("keskeneräinen", actual["description[fi]"].lower())
        self.assertEqual(actual["email"], "")
        self.assertIn("Antti Kajanus", actual["about"])
        self.assertIn("MIT", actual["about"])
        self.assertIn("GitHub Issues", actual["about"])
        self.assertIn("QGIS", actual["about"])
        self.assertIn("Qt", actual["about"])
        self.assertIn("GitHub Issues", actual["about[fi]"])
        self.assertTrue(actual["description[fi]"])
        self.assertEqual(actual["homepage"], "https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/tree/main/docs/help")
        self.assertEqual(actual["repository"], "https://github.com/anttikajanus/savonia-responsible-forest-planning-tool")
        self.assertEqual(actual["tracker"], "https://github.com/anttikajanus/savonia-responsible-forest-planning-tool/issues")

    def test_about_identity_uses_installed_metadata_including_utf8_and_literal_percent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "metadata.txt").write_text(
                "[general]\nname=Installed Metsä\nversion=9.8.7\nabout=100% installed\n",
                encoding="utf-8")
            actual = metadata(root)
            self.assertEqual(actual["name"], "Installed Metsä")
            self.assertEqual(actual["version"], "9.8.7")
            self.assertEqual(actual["about"], "100% installed")
            (root / "metadata.txt").write_text("[general]\nname=Missing version\n", encoding="utf-8")
            with self.assertRaises(ResourceError) as raised:
                metadata(root)
            self.assertEqual(raised.exception.reason, "invalid_metadata")

    def test_notices_and_licence_resolve_only_readable_known_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for resource, filename in (("licence", "LICENSE"), ("notices", "THIRD_PARTY_NOTICES"),
                                       ("inventory", "COMPONENT_INVENTORY.txt")):
                (root / filename).write_text("Original notice", encoding="utf-8")
                self.assertTrue(resource_url(resource, root).endswith("/" + filename))
                (root / filename).unlink()
                with self.assertRaises(ResourceError) as raised:
                    resource_url(resource, root)
                self.assertEqual(raised.exception.reason, "unreadable")
            with self.assertRaises(ResourceError) as raised:
                resource_url("../untrusted", root)
            self.assertEqual(raised.exception.reason, "unknown_resource")

    def test_missing_language_and_section_never_open_other_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs" / "help").mkdir(parents=True)
            (root / "docs" / "help" / "manual_en.html").write_text(
                '<h1 id="workflow">Workflow</h1>', encoding="utf-8")
            for language, section, reason in (("de", "workflow", "unsupported_language"),
                                              ("fi", "workflow", "unreadable"),
                                              ("en", "processing", "missing_section")):
                with self.subTest(language=language, section=section):
                    with self.assertRaises(ResourceError) as raised:
                        manual_url(language, section, root)
                    self.assertEqual(raised.exception.reason, reason)
                    self.assertTrue(raised.exception.resource)

    def test_manual_url_preserves_selected_language_and_encodes_installed_path(self):
        with tempfile.TemporaryDirectory(prefix="Metsä help ") as folder:
            root = Path(folder)
            (root / "docs" / "help").mkdir(parents=True)
            for language in ("fi", "en"):
                (root / "docs" / "help" / f"manual_{language}.html").write_text(
                    '<h1 id="workflow">Workflow</h1><h2 id="processing">Processing</h2>',
                    encoding="utf-8")
                url = manual_url(language, "processing", root)
                parsed = urlsplit(url)
                self.assertEqual(parsed.scheme, "file")
                self.assertEqual(parsed.fragment, "processing")
                self.assertTrue(unquote(parsed.path).endswith(f"/docs/help/manual_{language}.html"))
                self.assertIn("Mets%C3%A4%20help%20", url)


if __name__ == "__main__":
    unittest.main()
