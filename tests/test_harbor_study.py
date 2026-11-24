import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/exoverse/bin/exoverse-plugin"


class HarborStudyTest(unittest.TestCase):
    def test_import_verify_and_reject_score_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def write(name, data):
                output = root / name
                output.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")))
                return output

            def cli(*args, code=0):
                done = subprocess.run([sys.executable, str(PLUGIN), *map(str, args)],
                                      text=True, capture_output=True)
                self.assertEqual(done.returncode, code, done.stdout + done.stderr)
                return json.loads(done.stdout)

            source = write("protocol", {
                "question": "Does the agent change procedure compliance?",
                "hypothesis": "The candidate complies more often.",
                "environment": {"adapter": "harbor", "task_name": "review", "task_checksum": "fixture-checksum"},
                "rubric": {"minimum_rewards": {"reviewed": 1}},
                "judge": {"model": "planned"},
                "seeds": [0],
                "budget_microusd": 0,
                "stopping_rule": "One trial per arm.",
                "variables": {"agent": "nop"},
            })
            base, candidate, evidence, draft = (root / x for x in ("base", "candidate", "evidence", "draft"))
            parent = cli("spec", "freeze", source, "--out", base)["sha256"]
            child = cli("spec", "branch", base, "agent", write("replacement", "oracle"),
                        "--parent-sha256", parent, "--out", candidate)["sha256"]

            def trial(agent, reward):
                return {
                    "id": agent, "task_name": "review", "task_checksum": "fixture-checksum",
                    "agent_info": {"name": agent}, "finished_at": "fixture",
                    "config": {"agent": {"name": agent}, "environment": {"type": "docker"}},
                    "exception_info": None, "verifier_result": {"rewards": {"reviewed": reward}},
                }

            left = write("left", trial("nop", 0))
            right = write("right", trial("oracle", 1))
            imported = cli("harbor", "import", base, candidate, left, right,
                           "--parent-sha256", parent, "--candidate-sha256", child, "--out", evidence)
            self.assertEqual([row["passed"] for row in imported["results"]], [False, True])
            self.assertEqual(imported["judge_status"], "pending")
            verified = cli("harbor", "verify", evidence, "--sha256", imported["sha256"], "--draft", draft)
            self.assertTrue(verified["verified"])
            self.assertIn(imported["sha256"], draft.read_text())
            corrupted = json.loads(evidence.read_bytes())
            corrupted["results"][0]["passed"] = True
            write("evidence", corrupted)
            cli("harbor", "verify", evidence, "--sha256", hashlib.sha256(evidence.read_bytes()).hexdigest(), code=1)
            failed = trial("oracle", 0)
            failed["exception_info"] = {"exception_type": "SetupFailed"}
            write("right", failed)
            cli("harbor", "import", base, candidate, left, right,
                "--parent-sha256", parent, "--candidate-sha256", child, "--out", root / "failed", code=1)
