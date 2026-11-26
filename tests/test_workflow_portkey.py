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

    def test_independent_gateways_preserve_holds_on_transport_failure(self):
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import closing
        import sqlite3
        from urllib.error import URLError

        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "pilot.sqlite"
            RequestBudget(ledger).initialize(cap_microusd=200_000_000, request_limit=6)
            policy = ModelPolicy("fixed-model", 100_000, 500, 999, 200)
            models = {"claude": policy, "codex": policy}

            def fail_after_reservation(*args, **kwargs):
                with closing(sqlite3.connect(ledger)) as db:
                    reserved, = db.execute("SELECT SUM(amount) FROM holds").fetchone()
                self.assertGreaterEqual(reserved, 100_000_000)
                raise URLError("synthetic transport failure")

            gateways = [PortkeyGateway(key="fixture", budget=RequestBudget(ledger), models=models)
                        for _ in range(2)]
            for gateway in gateways:
                gateway._opener = MagicMock()
                gateway._opener.open.side_effect = fail_after_reservation
            body = b'{"model":"fixed-model","input":"choose"}'

            def forward(gateway):
                with self.assertRaisesRegex(ValueError, "reservation remains held"):
                    gateway.forward("codex", "/responses", body)

            with ThreadPoolExecutor(max_workers=2) as workers:
                list(workers.map(forward, gateways))
            for gateway in gateways:
                with self.assertRaises(BudgetRefused):
                    gateway.forward("codex", "/responses", body)
                gateway._opener.open.assert_called_once()

    def test_frozen_pilot_refuses_replacement_ledger_and_changed_prices(self):
        from dataclasses import replace
        from workflow_portkey import pilot_policy_sha256

        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "approved.sqlite"
            replacement = Path(root) / "replacement.sqlite"
            protocol = "a" * 64
            policy = ModelPolicy("fixed-model", 100_000, 500, 999, 200)
            models = {"claude": policy, "codex": policy}
            fingerprint = pilot_policy_sha256(protocol, models)
            binding = RequestBudget(ledger).initialize(
                cap_microusd=200_000_000, request_limit=6, policy_sha256=fingerprint)
            RequestBudget(replacement).initialize(
                cap_microusd=200_000_000, request_limit=6, policy_sha256=fingerprint)
            body = b'{"model":"fixed-model","input":"choose"}'

            def gateway(path, policies=models):
                return PortkeyGateway.for_frozen_pilot(
                    key="fixture", ledger_path=path, binding=binding,
                    protocol_sha256=protocol, models=policies)

            with self.assertRaisesRegex(BudgetRefused, "model policy differs"):
                gateway(ledger, {**models, "codex": replace(policy, output_microusd_per_token=1)})

            for instance in (gateway(ledger), gateway(ledger)):
                instance._opener = MagicMock()
                instance._opener.open.return_value.__enter__.return_value.read.return_value = b"fixture"
                self.assertEqual(instance.forward("codex", "/responses", body), b"fixture")
            for path in (ledger, replacement):
                instance = gateway(path)
                instance._opener = MagicMock()
                with self.assertRaises(BudgetRefused):
                    instance.forward("codex", "/responses", body)
                instance._opener.open.assert_not_called()
