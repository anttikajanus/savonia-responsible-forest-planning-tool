"""Offline manuals, legal texts and notices remain usable after packaging."""

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
        root = Path(os.environ.get(
            "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT",
            str(Path(__file__).resolve().parents[1]),
        ))
        self.package = root / "savonia_responsible_forest_planning_tool"
        self.help = self.package / "docs" / "help"
        self.resource_root = self.package
        self.licence = self.package / "LICENSE"
        if "RESPONSIBLE_FOREST_PLANNING_TEST_PLUGIN_ROOT" not in os.environ:
            self.resource_root = root.parent
            self.help = root.parent / "docs" / "help"
            self.licence = root.parent / "LICENSE"

    def test_both_manuals_have_equivalent_sections_and_valid_offline_links(self):
        required = {"workflow", "setup", "sources", "area", "wizard", "processing",
                    "outputs", "map-review", "limitations", "troubleshooting", "credits", "data-sources"}
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

    def test_original_legal_texts_and_dataset_credits_are_available_offline(self):
        licence = self.licence.read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Antti Kajanus", licence)
        self.assertIn("Permission is hereby granted, free of charge", licence)
        self.assertIn("THE SOFTWARE IS PROVIDED", licence)
        self.assertIn("OUT OF OR IN CONNECTION WITH THE SOFTWARE", licence)
        cc = (self.package / "licenses" / "CC-BY-4.0.txt").read_text(encoding="utf-8")
        notices = (self.package / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
        self.assertGreater(len(cc), 18000)
        self.assertIn("Section 8 -- Interpretation", cc)
        self.assertNotIn(cc.strip(), notices)
        self.assertIn("licenses/CC-BY-4.0.txt", notices)
        for credit in ("Suomen metsäkeskus", "Metsähallitus", "Lupa- ja valvontavirasto",
                       "Rantaviiva10-aineisto, Lähde: Syke, MML", "OpenStreetMap contributors"):
            self.assertIn(credit, notices)


if __name__ == "__main__":
    unittest.main()
