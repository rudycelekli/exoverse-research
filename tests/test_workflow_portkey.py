import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/exoverse/bin"))

from workflow_portkey import ModelPolicy, PortkeyGateway
from workflow_request_budget import BudgetRefused, RequestBudget


class PortkeyGatewayTest(unittest.TestCase):
    def test_routes_share_budget_before_transport(self):
        with tempfile.TemporaryDirectory() as root:
            budget = RequestBudget(Path(root) / "pilot.sqlite")
            budget.initialize(cap_microusd=200_000_000, request_limit=6)
            policy = ModelPolicy("fixed-model", 100_000, 500, 999, 200)
            gateway = PortkeyGateway(key="fixture", budget=budget,
                                     models={"claude": policy, "codex": policy})
            gateway._opener = MagicMock()
            gateway._opener.open.return_value.__enter__.return_value.read.return_value = b"fixture"
            claude = json.dumps({"model": "fixed-model", "messages": [{"role": "user", "content": "choose"}]}).encode()
            codex = b'{"model":"fixed-model","input":"choose"}'
            with self.assertRaises(BudgetRefused):
                gateway.forward("codex", "/messages", codex)
            with self.assertRaises(BudgetRefused):
                gateway.forward("codex", "/responses", b'{"model":"other","input":"choose"}')
            with self.assertRaises(BudgetRefused):
                gateway.forward("codex", "/responses", b'{"model":"fixed-model","input":"choose","stream":true}')
            gateway._opener.open.assert_not_called()
            self.assertEqual(gateway.forward("claude", "/messages", claude), b"fixture")
            self.assertEqual(gateway.forward("codex", "/responses", codex), b"fixture")
            for call, (endpoint, route) in zip(gateway._opener.open.call_args_list,
                                               [("/messages", "@anthropic"), ("/responses", "@openai")]):
                request = call.args[0]
                self.assertEqual(request.full_url, "https://api.portkey.ai/v1" + endpoint)
                self.assertEqual(request.get_header("X-portkey-provider"), route)
            with self.assertRaises(BudgetRefused):
                gateway.forward("codex", "/responses", codex)
            self.assertEqual(gateway._opener.open.call_count, 2)
