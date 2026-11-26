import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ResearchProjectTest(unittest.TestCase):
    def test_draft_replays_and_rejects_changed_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project.sqlite"
            draft = Path(folder) / "paper.md"
            def command(*args):
                return subprocess.run(
                    [sys.executable, str(ROOT / "plugins/exoverse/bin/exoverse-plugin"),
                     "project", str(project), *args], capture_output=True, text=True, cwd=ROOT,
                )
            self.assertEqual(command("init", "--question", "Does review help?").returncode, 0)
            first = command("run", "examples/review-workflow.json")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(command("run", "examples/review-workflow.json").returncode, 0)
            fingerprint = json.loads(first.stdout)["sha256"]
            self.assertEqual(json.loads(command("list").stdout)["studies"], [fingerprint])
            exported = command("draft", str(draft))
            self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
            self.assertIn(fingerprint, draft.read_text())
            with sqlite3.connect(project) as db:
                db.execute("UPDATE studies SET evidence = ?", (b"{}",))
            changed = Path(folder) / "changed.md"
            self.assertEqual(command("draft", str(changed)).returncode, 1)
            self.assertFalse(changed.exists())
