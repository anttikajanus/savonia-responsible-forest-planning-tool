"""Offline manuals, legal resources and inventory describe the actual package."""

from html import unescape
from html.parser import HTMLParser
import os
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit


class HtmlResources(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.anchors = set()
        self.links = []
        self.remote_dependencies = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.anchors.add(attributes["id"])
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        for key in ("src", "href"):
            value = attributes.get(key, "")
            if tag != "a" and urlsplit(value).scheme in ("http", "https"):
                self.remote_dependencies.append(value)


class HelpContentTests(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ.get("SAVONIA_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1])))
        self.package = root / "savonia_responsible_forest_planning_tool"
        self.help = self.package / "docs" / "help"
        self.resource_root = self.package
        if "SAVONIA_TEST_PLUGIN_ROOT" not in os.environ:
            self.resource_root = root.parent
            self.help = root.parent / "docs" / "help"

    def test_both_manuals_have_equivalent_sections_and_valid_offline_links(self):
        required = {"workflow", "installation", "setup", "sources", "area", "wizard", "processing",
                    "outputs", "limitations", "troubleshooting", "credits", "data-sources"}
        documents = {}
        for language in ("fi", "en"):
            path = self.help / f"manual_{language}.html"
            text = path.read_text(encoding="utf-8")
            header = unescape(text.split("</header>", 1)[0])
            self.assertIn("Savonia - Responsible Forest Planning" if language == "en"
                          else "Savonia - Vastuullinen metsäsuunnittelu", header)
            self.assertIn("Antti Kajanus" if language == "en" else "Antti Kajanuksen", header)
            self.assertIn("personal learning prototype" if language == "en" else "henkilökohtainen oppimisprototyyppi", header)
            self.assertIn("approved by Savonia in any form" if language == "en" else "millään tavoin hyväksymiä", header)
            documents[path.resolve()] = HtmlResources(text)
        for path, document in documents.items():
            with self.subTest(manual=path.name):
                self.assertTrue(required.issubset(document.anchors))
                self.assertEqual(document.remote_dependencies, [])
                for href in document.links:
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        continue
                    target = (path.parent / unquote(url.path)).resolve() if url.path else path
                    self.assertTrue(target.is_relative_to(self.resource_root.resolve()), href)
                    self.assertTrue(target.is_file(), href)
                    if url.fragment:
                        parsed = documents.get(target)
                        if parsed is None:
                            parsed = HtmlResources(target.read_text(encoding="utf-8"))
                        self.assertIn(unquote(url.fragment), parsed.anchors, href)

    def test_full_original_legal_texts_and_inventory_cover_distributed_files(self):
        licence = (self.package / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Antti Kajanus", licence)
        self.assertIn("Permission is hereby granted, free of charge", licence)
        self.assertIn("THE SOFTWARE IS PROVIDED", licence)
        self.assertIn("OUT OF OR IN CONNECTION WITH THE SOFTWARE", licence)
        cc = (self.package / "licenses" / "CC-BY-4.0.txt").read_text(encoding="utf-8")
        notices = (self.package / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
        self.assertGreater(len(cc), 18000)
        self.assertIn("Section 8 -- Interpretation", cc)
        self.assertIn(cc.strip(), notices)
        inventory = (self.package / "COMPONENT_INVENTORY.txt").read_text(encoding="utf-8")
        self.assertIn("HOST-PROVIDED DEPENDENCIES", inventory)
        self.assertIn("EXTERNAL DATA AND SERVICES", inventory)
        for path in self.package.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(self.package)
            if path.suffix == ".py" and len(relative.parts) > 1:
                self.assertIn(relative.parts[0] + "/", inventory)
                continue
            self.assertIn(relative.as_posix(), inventory, str(relative))


if __name__ == "__main__":
    unittest.main()
