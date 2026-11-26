"""Exercise the standalone public plugin through its CLI and MCP entry points."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/exoverse/bin/exoverse-plugin"
QUESTION = "Does exploring less lead to less missed reward in this simulation?"
EXPLORATION_DIGEST = "60484f1ff0ec81a0a47466a9f68711a2baa1e00576a5bd75daba446e0eb9a16d"


class FirstStudyTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="exoverse qualification ")
        self.addCleanup(workspace.cleanup)
        self.workspace = Path(workspace.name)

    def cli(self, *arguments, code=0):
        result = subprocess.run(
            [str(PLUGIN), *arguments], cwd=self.workspace,
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_starter_guess_is_optional_and_does_not_change_results(self):
        starter = self.cli("starter", "run", "--out", "starter.json")
        self.assertEqual(starter["receipt"]["prediction"], "skip")
        self.assertEqual(starter["model_calls"], 0)
        for guess in ("adaptive", "even"):
            candidate = self.cli("starter", "run", "--prediction", guess)["receipt"]
            self.assertEqual(candidate.pop("prediction"), guess)
            reference = {key: value for key, value in starter["receipt"].items() if key != "prediction"}
            self.assertEqual(candidate, reference)
        self.assertTrue(self.cli("starter", "verify", "starter.json", "--sha256", starter["sha256"])["verified"])

    def test_copy_verify_and_reproduce_the_trial_guide_study(self):
        arguments = (
            "paired", "run", "--question", QUESTION, "--baseline", "200",
            "--treatment", "50", "--prediction", "lower", "--out",
        )
        report = self.cli(*arguments, "first-study")
        self.assertEqual(report["sha256"], EXPLORATION_DIGEST)
        self.assertEqual(report["model_calls"], 0)
        original = self.workspace / "first-study"
        recipient = self.workspace / "recipient"
        copied = recipient / "first-study"
        shutil.copytree(original, copied)
        verify = ("paired", "verify", str(copied), "--sha256")
        self.assertTrue(self.cli(*verify, EXPLORATION_DIGEST)["verified"])
        reproduced = recipient / "reproduced-study"
        self.cli(*arguments, str(reproduced))
        for name in ("study.json", "paper.md"):
            self.assertEqual((original / name).read_bytes(), (reproduced / name).read_bytes())

        self.assertIn("error", self.cli(*verify, "0" * 64, code=1))
        with (copied / "paper.md").open("ab") as draft:
            draft.write(b"\nEdited draft\n")
        rejected = self.cli(*verify, EXPLORATION_DIGEST, code=1)
        self.assertIn("paper draft did not reproduce", rejected["error"])

    def test_installed_mcp_contract_accepts_and_rejects_expected_inputs(self):
        requests = [
            {"method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"method": "tools/list"},
            {"method": "tools/call", "params": {"name": "exoverse_run_first_study", "arguments": {}}},
            {"method": "tools/call", "params": {"name": "exoverse_run_local_comparison", "arguments": {
                "question": QUESTION, "baseline": 200, "treatment": 50, "prediction": "lower",
            }}},
            {"method": "tools/call", "params": {"name": "exoverse_run_local_comparison", "arguments": {
                "question": QUESTION, "baseline": 200, "treatment": 200, "prediction": "lower",
            }}},
        ]
        frames = "".join(
            json.dumps({"jsonrpc": "2.0", "id": index, **request}) + "\n"
            for index, request in enumerate(requests)
        )
        process = subprocess.run(
            [str(PLUGIN), "mcp", "starter"], cwd=self.workspace, input=frames,
            capture_output=True, text=True, timeout=15, check=True,
        )
        replies = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([reply["id"] for reply in replies], list(range(len(requests))))
        handshake, listing, starter, comparison, rejected = [reply["result"] for reply in replies]
        self.assertEqual(handshake["serverInfo"]["name"], "exoverse-starter")
        self.assertEqual({tool["name"] for tool in listing["tools"]}, {
            "exoverse_run_first_study", "exoverse_verify_first_study",
            "exoverse_run_local_comparison", "exoverse_run_monitor_comparison",
            "exoverse_verify_local_comparison",
        })
        self.assertEqual(json.loads(starter["content"][0]["text"])["receipt"]["prediction"], "skip")
        self.assertEqual(json.loads(comparison["content"][0]["text"])["sha256"], EXPLORATION_DIGEST)
        self.assertTrue(rejected["isError"])
        self.assertIn("different values", rejected["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
