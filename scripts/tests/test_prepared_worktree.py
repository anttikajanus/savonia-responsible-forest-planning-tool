"""Worktree preparation through the command entry point and real temporary Git repositories."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import prepare_worktree as prepare


@unittest.skipUnless(shutil.which("git"), "Git command is required")
class PreparedWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        isolation = patch.dict(os.environ, {"ProgramFiles": str(self.root / "ProgramFiles")})
        isolation.start()
        self.addCleanup(isolation.stop)
        self.git("init")
        (self.root / ".gitignore").write_text(".local/\n.scratch/\n", encoding="utf-8")
        (self.root / "scripts").mkdir()
        (self.root / "scripts/qgis-runtimes.json").write_text(json.dumps({
            "default_version": "3.44.0", "runtimes": [{"version": "3.44.0", "sha256": "a" * 64,
                                                        "launcher": "python-qgis.bat"}],
        }), encoding="utf-8")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
        self.spec = self.root / ".scratch/feature/spec.md"
        self.spec.parent.mkdir(parents=True)
        self.spec.write_text("Status: ready-for-agent\n", encoding="utf-8")

    def git(self, *arguments):
        return subprocess.run(["git", *arguments], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def invoke(self, *arguments):
        with patch.object(prepare, "ROOT", self.root), redirect_stdout(StringIO()) as output, redirect_stderr(StringIO()) as error:
            result = prepare.main(list(arguments))
        return result, output.getvalue(), error.getvalue()

    def test_prepared_worktree_records_base_spec_and_shared_environment_paths(self):
        environment = self.root / ".local/dev-environment"
        python = environment / "venv/Scripts/python.exe"
        python.parent.mkdir(parents=True)
        python.touch()
        site = environment / "venv/Lib/site-packages"
        site.mkdir(parents=True)
        (environment / "environment.json").write_text(json.dumps({
            "tooling_ready": True, "python": str(python), "tooling_path": str(site),
        }))
        result, output, _error = self.invoke("--name", "r01", "--spec", ".scratch/feature/spec.md")
        self.assertEqual(result, 0)
        context = json.loads(output)
        worktree = self.root / ".local/wt/r01"
        self.assertEqual(Path(context["worktree"]), worktree)
        self.assertEqual(Path(context["spec"]), self.spec)
        self.assertEqual(context["base_revision"], self.git("rev-parse", "HEAD"))
        self.assertTrue(context["preparer_git_metadata_writable"])
        self.assertEqual(Path(context["python"]), python)
        self.assertEqual(Path(context["tooling_path"]), site)
        self.assertEqual(self.git("-C", str(worktree), "rev-parse", "HEAD"), context["base_revision"])
        self.assertTrue(Path(context["context_file"]).is_file())
        # A worker running from the linked checkout receives the primary spec path.
        with patch.object(prepare, "ROOT", worktree), redirect_stdout(StringIO()) as probe_output:
            self.assertEqual(prepare.main(["--probe"]), 0)
        self.assertEqual(Path(json.loads(probe_output.getvalue())["shared_checkout"]), self.root)
        with patch.object(prepare, "ROOT", worktree), redirect_stdout(StringIO()) as linked_output:
            self.assertEqual(prepare.main(["--name", "r02", "--spec", ".scratch/feature/spec.md"]), 0)
        linked_context = json.loads(linked_output.getvalue())
        self.assertEqual(linked_context["python"], str(python))
        self.assertEqual(linked_context["spec"], str(self.spec))
        self.git("worktree", "remove", linked_context["worktree"])
        self.git("worktree", "remove", str(worktree))

    def test_invalid_name_or_missing_spec_creates_no_branch_or_worktree(self):
        before = self.git("branch", "--list")
        for name, spec in (("../../outside", str(self.spec)), ("x" * 17, str(self.spec)),
                           ("r02", ".scratch/missing.md")):
            with self.subTest(name=name):
                self.assertEqual(self.invoke("--name", name, "--spec", spec)[0], 1)
                self.assertEqual(self.git("branch", "--list"), before)
                self.assertFalse((self.root / ".local/wt/r02").exists())

    def test_denied_git_write_probe_reports_operation_before_creating_a_branch(self):
        before = self.git("branch", "--list")
        with patch.object(prepare.os, "open", side_effect=PermissionError("fixture denied")):
            result, output, error = self.invoke("--name", "r03", "--spec", str(self.spec))
        self.assertEqual(result, 1)
        access = json.loads(output)
        self.assertFalse(access["git_metadata_writable"])
        self.assertEqual("create probe file", access["probes"][0]["operation"])
        self.assertIn("authorized owner", error)
        self.assertEqual(self.git("branch", "--list"), before)
        self.assertFalse((self.root / ".local/wt/r03").exists())


if __name__ == "__main__":
    unittest.main()
