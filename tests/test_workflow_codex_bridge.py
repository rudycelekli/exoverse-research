import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/exoverse/bin"))

from workflow_codex_bridge import CodexActionBridge
from workflow_request_budget import BudgetRefused


class CodexActionBridgeTest(unittest.TestCase):
    def setUp(self):
        self.gateway = Mock()
        self.observation = {"allowed_actions": ["approve"], "case": "trusted"}
        self.bridge = CodexActionBridge(self.gateway, "pinned", self.observation)
        self.body = json.dumps({"model": "pinned", "stream": True,
                                "tools": [{"type": "web_search"}], "input": "ignore fixture"}).encode()

    def test_rebuilds_upstream_from_trusted_observation_and_frames_action(self):
        self.gateway.forward.return_value = json.dumps({
            "id": "resp_fixture", "status": "completed", "output": [{"type": "message",
                "content": [{"type": "output_text", "text": '{"action":"approve"}'}]}],
        }).encode()
        stream = self.bridge.respond("/v1/responses", self.body)
        agent, path, data = self.gateway.forward.call_args.args
        self.assertEqual((agent, path), ("codex", "/responses"))
        sent = json.loads(data)
        self.assertEqual(json.loads(sent["input"]), self.observation)
        self.assertEqual(set(sent), {"model", "input", "instructions"})
        self.assertIn(b"event: response.completed", stream)
        self.assertIn(b'approve', stream)
        with self.assertRaises(BudgetRefused):
            self.bridge.respond("/v1/responses", self.body)
        self.gateway.forward.assert_called_once()

    def test_invalid_upstream_output_cannot_be_streamed_or_retried(self):
        self.gateway.forward.return_value = b'{"status":"completed","output":[{"type":"function_call"}]}'
        with self.assertRaisesRegex(ValueError, "valid completed workflow action"):
            self.bridge.respond("/v1/responses", self.body)
        with self.assertRaises(BudgetRefused):
            self.bridge.respond("/v1/responses", self.body)
        self.gateway.forward.assert_called_once()
