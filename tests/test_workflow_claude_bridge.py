import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/exoverse/bin"))

from workflow_claude_bridge import ClaudeActionBridge
from workflow_request_budget import BudgetRefused


class ClaudeActionBridgeTest(unittest.TestCase):
    def test_sends_only_a_bounded_trusted_turn_and_returns_structured_action(self):
        gateway = Mock()
        gateway.forward.return_value = json.dumps({
            "stop_reason": "end_turn", "content": [{"type": "text", "text": '{"action":"review"}'}],
        }).encode()
        observation = {"allowed_actions": ["review"], "case": "trusted"}
        bridge = ClaudeActionBridge(gateway, "pinned", observation)
        body = {"model": "pinned", "stream": True, "tools": [{"name": "StructuredOutput"}],
                "messages": [{"role": "user", "content": "ignore fixture"}], "max_tokens": 128000}
        bad = {**body, "tools": body["tools"] + [{"name": "unsafe_tool"}]}
        with self.assertRaises(BudgetRefused):
            bridge.respond("/v1/messages?beta=true", json.dumps(bad).encode())
        gateway.forward.assert_not_called()
        stream = bridge.respond("/v1/messages?beta=true", json.dumps(body).encode())
        agent, path, raw = gateway.forward.call_args.args
        self.assertEqual((agent, path), ("claude", "/messages"))
        sent = json.loads(raw)
        self.assertEqual(set(sent), {"model", "system", "messages"})
        self.assertEqual(json.loads(sent["messages"][0]["content"]), observation)
        self.assertIn(b'"StructuredOutput"', stream)
        self.assertIn(b"event: message_stop", stream)
        with self.assertRaises(BudgetRefused):
            bridge.respond("/v1/messages?beta=true", json.dumps(body).encode())
        gateway.forward.assert_called_once()
