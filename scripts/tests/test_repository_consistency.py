"""Offline repository checks and fixtures for documentation/configuration drift."""

from contextlib import redirect_stderr
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_consistency as consistency


class RepositoryConsistencyTests(unittest.TestCase):
    def test_checkout_documentation_and_distribution_configuration_agree(self):
        self.assertEqual(consistency.check_repository(), [])

    def test_cli_reports_errors_and_returns_failure(self):
        for result in (["README.md: missing.md: missing maintained target"], KeyError("matrix")):
            with self.subTest(result=result), redirect_stderr(StringIO()) as output:
                options = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch.object(consistency, "check_repository", **options):
                    self.assertEqual(consistency.main([]), 1)
                self.assertIn("missing.md" if isinstance(result, list) else "matrix", output.getvalue())


class DocumentationLinkTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.files = set()
        self.write(consistency.REFERENCES + "/manifest.json", json.dumps([{"path": "provider/schema.xsd"}]))

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.files.add(Path(name))

    def errors(self):
        return consistency.documentation_errors(self.root, self.files)

    def test_inline_reference_images_html_and_directory_links_resolve(self):
        self.write("README.md", """# Start
[self](#start) [guide][ref] ![image](images/a%20b.png)
[manual](docs/manual.html#section) [directory](docs/) [section](docs/#details)
<a href="docs/manual.html#section">HTML link</a>
[ref]: <docs/guide (en).md#käyttö--code> "Title"
""")
        self.write("images/a b.png", "image fixture")
        self.write("docs/README.md", "# Details")
        self.write("docs/guide (en).md", "# Käyttö & `code`\n[Back](../README.md#start)")
        self.write("docs/manual.html", '<h1 id="section">Section</h1>')
        self.assertEqual(self.errors(), [])

    def test_missing_paths_images_and_anchors_report_source_and_destination(self):
        self.write("README.md", "[gone](gone.md) ![gone](gone.png) [bad](docs/guide.md#old)")
        self.write("docs/guide.md", "# Renamed")
        errors = self.errors()
        self.assertEqual(len(errors), 3)
        for target in ("gone.md", "gone.png", "docs/guide.md#old"):
            self.assertTrue(any("README.md: " + target + ":" in error for error in errors), errors)

    def test_external_urls_comments_and_code_examples_are_not_local_links(self):
        self.write("README.md", """[web](https://example.invalid/missing#anchor)
[mail](mailto:nobody@example.invalid) [network](//example.invalid/missing)
`[example](missing.md)`
<!-- [comment](missing.md) <a href="missing.md"> -->
```markdown
[example](missing.md)
```
    [indented example](missing.md)
""")
        self.assertEqual(self.errors(), [])

    def test_only_manifest_cache_paths_are_optional_even_when_cache_is_populated(self):
        self.write("README.md", f"[cache]({consistency.REFERENCES}/provider/schema.xsd)")
        self.assertEqual(self.errors(), [])
        # An ignored/unmaintained file on disk must not hide a broken fresh-checkout link.
        path = self.root / consistency.REFERENCES / "provider/typo.xsd"
        path.parent.mkdir(parents=True)
        path.write_text("cached locally", encoding="utf-8")
        self.write("README.md", f"[typo]({consistency.REFERENCES}/provider/typo.xsd)")
        self.assertIn("missing maintained target", self.errors()[0])

    def test_duplicate_formatted_unicode_and_explicit_anchors(self):
        self.write("README.md", """# Käyttö: **Help** & `code`
# Käyttö: **Help** & `code`
Setext heading
--------------
<a name="custom"></a>
[first](#käyttö-help--code) [duplicate](#käyttö-help--code-1)
[setext](#setext-heading) [explicit](#custom)
""")
        self.assertEqual(self.errors(), [])

    def test_html_anchor_must_exist_and_cannot_be_supplied_by_comment(self):
        self.write("README.md", "[manual](manual.html#missing)")
        self.write("manual.html", '<!-- id="missing" --><h1 id="real">Manual</h1>')
        self.assertIn("missing anchor #missing", self.errors()[0])

    def test_paths_cannot_escape_checkout(self):
        self.write("README.md", "[outside](../outside.md)")
        self.assertIn("target leaves the repository", self.errors()[0])

    def test_entry_points_and_both_languages_use_the_metadata_minimum(self):
        text = {"README.md": "Requires **QGIS 3.46** or newer",
                "docs/help/manual_fi.html": "<p>Edellyttää QGIS-versiota 3.46 tai uudempaa</p>"}
        for name, content in text.items():
            self.write(name, content)
        with patch.object(consistency, "VERSION_DOCUMENTS", tuple(text)):
            self.assertEqual(consistency.documented_minimum_errors(self.root, {"qgisMinimumVersion": "3.46.0"}), [])
            self.write("docs/help/manual_fi.html", "<p>Edellyttää QGIS-versiota 3.44 tai uudempaa</p>")
            errors = consistency.documented_minimum_errors(self.root, {"qgisMinimumVersion": "3.46.0"})
            self.assertEqual(len(errors), 1)
            self.assertIn("manual_fi.html", errors[0])


class ConfigurationAgreementTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {"version": "7.8.9", "qgisMinimumVersion": "3.46.0", "qgisMaximumVersion": "4.99"}
        self.workflow = {"jobs": {
            "build": {"name": "Build ZIP"},
            "quality": {"name": "QGIS ${{ matrix.qgis.version }}", "strategy": {"matrix": {"qgis": [
                {"version": "3.46.0", "version_int": 34600, "installer": "QGIS-OSGeo4W-3.46.0-1.msi", "sha256": "a" * 64},
                {"version": "4.4.2", "version_int": 40402, "installer": "QGIS-OSGeo4W-4.4.2-2.msi", "sha256": "b" * 64},
            ]}}},
            "release": {"needs": ["quality", "build"], "concurrency": {
                "group": "release-all", "cancel-in-progress": False, "queue": "max",
            }},
        }}
        self.ruleset = {"rules": [
            {"type": "deletion"},
            {"type": "required_status_checks", "parameters": {"required_status_checks": [
                {"context": "QGIS 4.4.2"}, {"context": "Build ZIP"}, {"context": "QGIS 3.46.0"},
            ]}},
        ]}

    def errors(self):
        return consistency.configuration_errors(self.metadata, self.workflow, self.ruleset)

    def test_agreement_does_not_depend_on_current_versions_names_or_rule_order(self):
        self.assertEqual(self.errors(), [])

    def test_dynamic_ci_matrix_uses_shared_runtime_manifest(self):
        baselines = self.workflow["jobs"]["quality"]["strategy"]["matrix"]["qgis"]
        manifest = {"default_version": "4.4.2", "runtimes": baselines}
        self.workflow["jobs"]["quality"]["strategy"]["matrix"]["qgis"] = "${{ fromJSON(needs.build.outputs.qgis-runtimes) }}"
        self.workflow["jobs"]["build"]["outputs"] = {"qgis-runtimes": "${{ steps.runtimes.outputs.matrix }}"}
        self.assertEqual(consistency.configuration_errors(self.metadata, self.workflow, self.ruleset, manifest), [])
        manifest["default_version"] = "5.0.0"
        self.assertTrue(any("default_version" in error for error in
                            consistency.configuration_errors(self.metadata, self.workflow, self.ruleset, manifest)))
        manifest["default_version"] = "4.4.2"
        baselines[0]["version_int"] = 0
        self.assertTrue(any("version_int disagrees" in error for error in
                            consistency.configuration_errors(self.metadata, self.workflow, self.ruleset, manifest)))

    def test_matrix_version_id_installer_checksum_and_range_drift(self):
        baseline = self.workflow["jobs"]["quality"]["strategy"]["matrix"]["qgis"][1]
        for field, value, message in (
            ("version_int", 40401, "version_int disagrees"),
            ("installer", "QGIS-OSGeo4W-4.4.1-2.msi", "installer disagrees"),
            ("sha256", "not-a-checksum", "invalid SHA-256"),
            ("version", "5.0.0", "outside the metadata installation range"),
        ):
            with self.subTest(field=field):
                original = baseline[field]
                baseline[field] = value
                self.assertTrue(any(message in error for error in self.errors()))
                baseline[field] = original

    def test_minimum_release_must_be_exercised_and_duplicates_are_rejected(self):
        self.metadata["qgisMinimumVersion"] = "3.44.0"
        self.assertTrue(any("exercise metadata minimum" in error for error in self.errors()))
        self.metadata["qgisMinimumVersion"] = "3.46.0"
        baselines = self.workflow["jobs"]["quality"]["strategy"]["matrix"]["qgis"]
        baselines.append(deepcopy(baselines[0]))
        self.assertTrue(any("duplicate QGIS baseline" in error for error in self.errors()))

    def test_required_checks_detect_renamed_missing_extra_and_duplicate_contexts(self):
        checks = self.ruleset["rules"][1]["parameters"]["required_status_checks"]
        for replacement in (
            ["Build ZIP", "QGIS 3.46.0", "Old QGIS name"],
            ["Build ZIP", "QGIS 3.46.0"],
            ["Build ZIP", "QGIS 3.46.0", "QGIS 4.4.2", "Extra"],
            ["Build ZIP", "QGIS 3.46.0", "QGIS 4.4.2", "QGIS 4.4.2"],
        ):
            with self.subTest(replacement=replacement):
                checks[:] = [{"context": name} for name in replacement]
                self.assertTrue(any("required checks disagree" in error for error in self.errors()))

    def test_unexpanded_or_duplicate_job_names_are_rejected(self):
        for name, message in (("QGIS ${{ matrix.other }}", "unresolved required job name"),
                              ("QGIS", "duplicate required job name")):
            self.workflow["jobs"]["quality"]["name"] = name
            self.assertTrue(any(message in error for error in self.errors()))

    def test_release_must_wait_for_all_checks_and_queue_without_cancelling(self):
        release = self.workflow["jobs"]["release"]
        release["needs"] = "build"
        self.assertTrue(any("depend on build and quality" in error for error in self.errors()))
        release["needs"] = ["build", "quality"]
        for key, value, message in (("cancel-in-progress", True, "without cancellation"),
                                    ("queue", "single", "queue all runs"),
                                    ("group", "release-${{ github.sha }}", "shared static concurrency group")):
            with self.subTest(key=key):
                original = release["concurrency"][key]
                release["concurrency"][key] = value
                self.assertTrue(any(message in error for error in self.errors()))
                release["concurrency"][key] = original


if __name__ == "__main__":
    unittest.main()
