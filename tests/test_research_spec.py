import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/exoverse/bin/exoverse-plugin"


class ResearchSpecTest(unittest.TestCase):
    def test_independent_verifier_rejects_rubric_change_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol, baseline, candidate, replacement = (root / filename for filename in
                                                           ("protocol", "baseline", "candidate", "replacement"))
            protocol.write_text(json.dumps({
                "question": "Does an explicit review step reduce procedure violations?",
                "hypothesis": "The review-first prompt reduces violations.",
                "environment": {"adapter": "harbor", "task_revision": "illustrative-fixture"},
                "rubric": {"requires_review": True},
                "judge": {"model": "fixture", "revision": "v1"},
                "seeds": [1, 2],
                "budget_microusd": 0,
                "stopping_rule": "Finish both arms for both seeds.",
                "variables": {"prompt": "Follow the procedure.", "toolset": "fixed"},
            }))
            replacement.write_text(json.dumps("Review before submission."))

            def cli(*args, valid=True):
                result = subprocess.run([sys.executable, str(PLUGIN), "spec", *map(str, args)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0 if valid else 1, result.stdout + result.stderr)
                return json.loads(result.stdout)

            parent = cli("freeze", protocol, "--out", baseline)["sha256"]
            baseline_bytes = baseline.read_bytes()
            child = cli("branch", baseline, "prompt", replacement, "--parent-sha256", parent,
                        "--out", candidate)["sha256"]
            self.assertEqual(baseline.read_bytes(), baseline_bytes)

            def verify(fingerprint, valid=True):
                return cli("verify", baseline, candidate, "--parent-sha256", parent,
                           "--candidate-sha256", fingerprint, valid=valid)

            self.assertTrue(verify(child)["verified"])
            for edited in (baseline_bytes + b" ", b'{"schema":"conflicting",' + baseline_bytes[1:]):
                baseline.write_bytes(edited)
                verify(child, valid=False)
                cli("branch", baseline, "prompt", replacement, "--parent-sha256", parent,
                    "--out", root / "refused", valid=False)
                self.assertFalse((root / "refused").exists())
            baseline.write_bytes(baseline_bytes)
            data = json.loads(candidate.read_bytes())
            data["protocol"]["rubric"]["requires_review"] = False
            changed = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
            candidate.write_bytes(changed)
            verify(hashlib.sha256(changed).hexdigest(), valid=False)
