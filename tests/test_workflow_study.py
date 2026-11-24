"""Exercise a user's own authored workflow through the standalone package."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[1] / "plugins/exoverse/bin/exoverse-plugin"


class WorkflowTest(unittest.TestCase):
    def test_rubric_distinguishes_two_paths_to_same_goal(self):
        spec = LAUNCHER.parents[3] / "examples/review-workflow.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.json"
            output = subprocess.check_output([str(LAUNCHER), "workflow", "run", str(spec), "--out", str(target)])
            rows = json.loads(output)["episodes"]
            self.assertTrue(all(row["final_state"] == "accepted" for row in rows.values()))
            self.assertEqual(rows["review-first"]["reward"], 1)
            self.assertEqual(rows["skip-review"]["reward"], 0)
            self.assertEqual(rows["skip-review"]["criteria"]["missing_required_states"], ["reviewed"])
            self.assertEqual(rows["skip-review"]["criteria"]["visited_forbidden_states"], ["bypassed"])

    def test_author_run_and_verify(self):
        payload = {
            "initial": "requested",
            "states": {"requested": {"review": "checked", "approve": "void"},
                       "checked": {"approve": "paid"}, "paid": {}, "void": {}},
            "criteria": {"goal": "paid", "within_steps": 2},
            "max_steps": 3,
            "policies": {"reviewer": {"requested": "review", "checked": "approve"},
                         "direct": {"requested": "approve", "checked": "approve"}},
        }
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "budget-workflow.json"
            evidence = workspace / "result.json"
            source.write_text(json.dumps(payload))
            generated = subprocess.check_output([str(LAUNCHER), "workflow", "run", str(source),
                                                 "--out", str(evidence)], cwd=workspace)
            report = json.loads(generated)
            self.assertEqual(report["episodes"]["reviewer"]["reward"], 1)
            self.assertEqual(report["episodes"]["direct"]["reward"], 0)
            self.assertEqual(report["episodes"]["direct"]["trace"][0]["state"], "requested")
            recipient = workspace / "recipient"
            recipient.mkdir()
            command = [str(LAUNCHER), "workflow", "verify", str(evidence), "--sha256"]
            verified = subprocess.check_output([*command, report["sha256"]], cwd=recipient)
            self.assertTrue(json.loads(verified)["verified"])
            altered = json.loads(evidence.read_bytes())
            altered["episodes"]["direct"]["reward"] = 1
            raw = json.dumps(altered, sort_keys=True, separators=(",", ":")).encode()
            evidence.write_bytes(raw)
            result = subprocess.run([*command, hashlib.sha256(raw).hexdigest()], cwd=recipient,
                                    capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b"did not reproduce", result.stdout)


if __name__ == "__main__":
    unittest.main()
