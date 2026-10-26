"""Release versioning and retries use local Git repositories, without GitHub."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_release import METADATA, git, metadata_version, prepare_release


class PrepareReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="Metsä release ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        git(self.root, "init", "--initial-branch=main")
        git(self.root, "config", "user.name", "Release test")
        git(self.root, "config", "user.email", "release@example.invalid")
        self.metadata = self.root / METADATA
        self.metadata.parent.mkdir(parents=True)
        self.metadata.write_text("[general]\nname=Metsä\nversion=1.0.0\n", encoding="utf-8")
        self.commit("Source")
        self.source = git(self.root, "rev-parse", "HEAD")

    def commit(self, message):
        git(self.root, "add", ".")
        git(self.root, "commit", "--allow-empty", "-m", message)

    def test_first_release_increases_minor_and_preserves_utf8(self):
        release = prepare_release(self.root)
        self.assertEqual((release.version, release.tag, release.existing), ("1.1.0", "v1.1.0", False))
        self.assertEqual(metadata_version(self.metadata.read_text(encoding="utf-8")), (1, 1, 0))
        self.assertIn("name=Metsä", self.metadata.read_text(encoding="utf-8"))
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), self.source)

    def test_tags_are_ordered_numerically_with_fixed_major_and_patch_reset(self):
        for tag in ("v1.9.9", "v1.10.5", "v2.99.0", "v1.99.0-rc1", "other"):
            git(self.root, "tag", tag)
        self.assertEqual(prepare_release(self.root).version, "1.11.0")

    def test_newer_source_metadata_is_the_version_floor(self):
        self.metadata.write_text("[general]\nversion=1.20.9\n", encoding="utf-8")
        git(self.root, "tag", "v1.10.0")
        self.assertEqual(prepare_release(self.root).version, "1.21.0")

    def test_retry_restores_the_same_tag_even_after_later_releases(self):
        first = prepare_release(self.root)
        self.commit(f"Release {first.tag}")
        git(self.root, "tag", first.tag)
        release_commit = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "--detach", self.source)
        self.commit("Next source")
        next_source = git(self.root, "rev-parse", "HEAD")
        second = prepare_release(self.root)
        self.assertEqual(second.version, "1.2.0")
        self.commit(f"Release {second.tag}")
        git(self.root, "tag", second.tag)
        git(self.root, "checkout", "--detach", self.source)
        retry = prepare_release(self.root)
        self.assertEqual((retry.version, retry.existing), ("1.1.0", True))
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), release_commit)
        self.assertEqual(metadata_version(self.metadata.read_text(encoding="utf-8")), (1, 1, 0))
        git(self.root, "checkout", "--detach", next_source)
        self.assertTrue(prepare_release(self.root).existing)

    def test_unrelated_child_tag_does_not_count_as_this_sources_release(self):
        self.commit("Unrelated change")
        git(self.root, "tag", "v1.1.0")
        git(self.root, "checkout", "--detach", self.source)
        self.assertEqual(prepare_release(self.root).version, "1.2.0")

    def test_invalid_metadata_stops_without_modifying_it(self):
        for value in ("1.2", "1.2.3-beta", "01.2.3"):
            with self.subTest(value=value):
                content = f"[general]\nversion={value}\n"
                self.metadata.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    prepare_release(self.root)
                self.assertEqual(self.metadata.read_text(encoding="utf-8"), content)

    def test_command_emits_github_outputs(self):
        script = Path(__file__).resolve().parents[1] / "prepare_release.py"
        output = self.root / "outputs.txt"
        subprocess.run([sys.executable, str(script), "--output", str(output)],
                       cwd=self.root, check=True, capture_output=True)
        self.assertEqual(output.read_text(encoding="utf-8"),
                         "version=1.1.0\ntag=v1.1.0\nexisting=false\n")


if __name__ == "__main__":
    unittest.main()
