import http.client
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/exoverse/bin"))

from workflow_action_loopback import action_loopback


class ActionLoopbackTest(unittest.TestCase):
    def test_two_endpoints_require_separate_turn_tokens(self):
        for agent in ("claude", "codex"):
            with self.subTest(agent=agent):
                bridge = Mock()
                bridge.respond.return_value = b"event: completed\n\n"
                with action_loopback(agent, bridge) as endpoint:
                    address = urlsplit(endpoint.base_url)
                    self.assertEqual(address.hostname, "127.0.0.1")
                    key = "x-api-key" if agent == "claude" else "Authorization"
                    value = endpoint.token if agent == "claude" else "Bearer " + endpoint.token

                    def post(headers):
                        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=2)
                        try:
                            connection.request("POST", "/fixture", b"{}", headers)
                            response = connection.getresponse()
                            return response.status, response.getheader("Content-Type"), response.read()
                        finally:
                            connection.close()

                    self.assertEqual(post({key: "wrong"})[0], 401)
                    self.assertEqual(post({key: value, "Content-Length": "999999"})[0], 413)
                    bridge.respond.assert_not_called()
                    self.assertEqual(post({key: value}), (200, "text/event-stream", bridge.respond.return_value))
                    bridge.respond.assert_called_once_with("/fixture", b"{}")
                    self.assertNotIn(endpoint.token, repr(endpoint))
