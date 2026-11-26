"""Authenticated, loopback-only transport for one native workflow turn."""

from contextlib import contextmanager
from dataclasses import dataclass
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
from secrets import token_urlsafe
from threading import Thread

from workflow_portkey import MAX_BODY_BYTES
from workflow_request_budget import BudgetRefused


@dataclass(frozen=True, repr=False)
class LoopbackEndpoint:
    base_url: str
    token: str


@contextmanager
def action_loopback(agent, bridge):
    if agent not in {"claude", "codex"}:
        raise ValueError("Unknown native workflow agent.")
    token = token_urlsafe(32)
    auth_name, auth_value = ("x-api-key", token) if agent == "claude" else ("Authorization", f"Bearer {token}")
    expected = auth_value.encode("ascii")

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, *_args):
            # The listener never logs request information.
            pass

        def _write(self, status, content_type, body):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status, message):
            body = json.dumps({"error": {"type": "invalid_request_error", "message": message}}).encode()
            self._write(status, "application/json", body)

        def do_POST(self):
            auth = self.headers.get_all(auth_name, [])
            if len(auth) != 1 or not compare_digest(auth[0].encode("latin1"), expected):
                self._error(401, "Workflow listener requires its turn token.")
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,6}", lengths[0]) or self.headers.get_all("Transfer-Encoding"):
                self._error(400, "A single bounded request length is required.")
                return
            size = int(lengths[0])
            if not 0 < size <= MAX_BODY_BYTES:
                self._error(413, "Workflow request exceeds its body limit.")
                return
            try:
                raw = self.rfile.read(size)
                if len(raw) != size:
                    self._error(400, "Workflow request is truncated.")
                    return
                reply = bridge.respond(self.path, raw)
            except TimeoutError:
                self._error(408, "Workflow request timed out.")
                return
            except BudgetRefused:
                self._error(429, "Workflow request was refused.")
                return
            except (OSError, ValueError):
                self._error(502, "Workflow action was unavailable.")
                return
            self._write(200, "text/event-stream", reply)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        worker.start()
        try:
            yield LoopbackEndpoint(f"http://127.0.0.1:{server.server_port}", token)
        finally:
            server.shutdown()
            worker.join()
