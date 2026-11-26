"""Exercise native CLI adapters with offline, contract-shaped stand-ins."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/exoverse/bin/exoverse-plugin"
CREDENTIALS = {
    "ANTHROPIC_API_KEY": "fixture-anthropic-key",
    "ANTHROPIC_BASE_URL": "https://anthropic.example.invalid",
    "CLAUDE_CODE_OAUTH_TOKEN": "fixture-claude-token",
    "OPENAI_API_KEY": "fixture-openai-key",
    "OPENAI_BASE_URL": "https://openai.example.invalid",
    "CODEX_HOME": "fixture-codex-home",
}
ADAPTER = """
import json, os, sys
from pathlib import Path

host = Path(sys.argv[0]).name
args = sys.argv[1:]
anthropic = {"ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN"}
openai = {"OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_HOME"}
forwarded = set(os.environ) & (anthropic | openai)
if args == ["--version"]:
    assert not forwarded
    print(host + " test adapter")
    raise SystemExit()
assert forwarded == (anthropic if host == "claude" else openai)
assert not Path("original-workflow.json").exists()
assert not Path("another-arm").exists()
Path("another-arm").touch()
Path("another-arm").unlink()
obs = json.loads(sys.stdin.read().split("\\n", 1)[1])
if host == "claude":
    assert "--bare" in args and args[args.index("--tools")+1] == ""
    assert "--strict-mcp-config" in args and "--no-session-persistence" in args
    chosen = "review" if obs["state"] == "draft" else "submit"
    print(json.dumps({"is_error": False, "num_turns": 1, "structured_output": {"action": chosen}}))
else:
    assert "--ignore-user-config" in args and "--ephemeral" in args
    assert args[args.index("--sandbox")+1] == "read-only" and "shell_tool" in args
    assert "--dangerously-bypass-approvals-and-sandbox" not in args
    Path(args[args.index("--output-last-message")+1]).write_text(json.dumps({"action": "submit"}))
"""


class LiveWorkflowTest(unittest.TestCase):
    def test_live_adapters_and_offline_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            binaries = work / "bin"
            binaries.mkdir()
            for name in ("claude", "codex"):
                stub = binaries / name
                stub.write_text("#!" + sys.executable + "\n" + ADAPTER)
                stub.chmod(0o700)
            spec = {"initial": "draft", "states": {"draft": {"review": "ready", "submit": "rejected"},
                    "ready": {"submit": "accepted"}, "accepted": {}, "rejected": {}},
                    "criteria": {"goal": "accepted", "within_steps": 2}, "max_steps": 2}
            (work / "original-workflow.json").write_text(json.dumps(spec))
            args = [sys.executable, str(PLUGIN), "workflow"]
            env = {**os.environ, **CREDENTIALS, "PATH": str(binaries) + os.pathsep + os.defpath}
            run = ["live", "original-workflow.json", "--max-calls", "4", "--out", "evidence.json"]
            refused = subprocess.run([*args, *run], cwd=work, env=env, capture_output=True)
            self.assertEqual(refused.returncode, 1)
            self.assertFalse((work / "evidence.json").exists())
            result = json.loads(subprocess.check_output([*args, *run, "--allow-model-calls"], cwd=work, env=env))
            self.assertEqual(result["agent_invocations"], 3)
            self.assertEqual(result["episodes"]["claude"]["reward"], 1)
            self.assertEqual(result["episodes"]["codex"]["reward"], 0)
            recipient = work / "recipient"
            recipient.mkdir()
            evidence = work / "evidence.json"
            replay = [*args, "verify", str(evidence), "--sha256"]
            offline = {**env, "PATH": str(recipient)}
            report = json.loads(subprocess.check_output([*replay, result["sha256"]], cwd=recipient, env=offline))
            self.assertTrue(report["verified"])
            self.assertEqual(report["model_calls"], 0)
            edited = json.loads(evidence.read_bytes())
            edited["episodes"]["claude"]["trace"][0]["action"] = "submit"
            altered = json.dumps(edited, sort_keys=True, separators=(",", ":")).encode()
            evidence.write_bytes(altered)
            check = subprocess.run([*replay, hashlib.sha256(altered).hexdigest()], cwd=recipient,
                                   env=offline, capture_output=True)
            self.assertEqual(check.returncode, 1)


if __name__ == "__main__":
    unittest.main()
