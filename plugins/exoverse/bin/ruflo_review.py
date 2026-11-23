"""Record a verified local alignment review in Ruflo's task store."""

from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import subprocess
import time
from pathlib import Path

RESPONSE_LIMIT = 1024 * 1024
RPC_TIMEOUT = 25
PROTOCOL = "2025-06-18"
SERVER_VERSION = "3.80.0"
TOOLS = ("task_create", "task_complete", "task_status")


def _digest(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Expected a lowercase SHA-256 digest.")
    return value


def _send(process: subprocess.Popen, message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}).encode() + b"\n")
    process.stdin.flush()


def _response(process: subprocess.Popen, stream: selectors.BaseSelector, pending: bytearray,
              request_id: int) -> dict:
    deadline = time.monotonic() + RPC_TIMEOUT
    observed = 0
    while True:
        while b"\n" in pending:
            end = pending.index(b"\n")
            raw = bytes(pending[:end])
            del pending[:end + 1]
            try:
                row = json.loads(raw)
            except (UnicodeError, ValueError, RecursionError):
                raise ValueError("Ruflo returned invalid stdio MCP output.") from None
            if not isinstance(row, dict) or row.get("jsonrpc") != "2.0":
                raise ValueError("Ruflo returned an invalid MCP message.")
            if row.get("id") == request_id:
                if "error" in row or not isinstance(row.get("result"), dict):
                    raise ValueError("Ruflo did not return a successful MCP response.")
                return row["result"]
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not stream.select(remaining):
            raise ValueError("The local Ruflo MCP server timed out.")
        assert process.stdout is not None
        chunk = os.read(process.stdout.fileno(), 4096)
        observed += len(chunk)
        if not chunk or observed > RESPONSE_LIMIT:
            raise ValueError("The local Ruflo MCP server closed or exceeded its response limit.")
        pending.extend(chunk)


def _tool_result(result: dict) -> dict:
    if result.get("isError"):
        raise ValueError("A local Ruflo task operation failed.")
    payload = result.get("structuredContent")
    if not isinstance(payload, dict):
        parts = result.get("content")
        if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
            raise ValueError("Ruflo returned an unsupported task result.")
        try:
            payload = json.loads(parts[0]["text"])
        except (KeyError, TypeError, ValueError, RecursionError):
            raise ValueError("Ruflo returned an invalid task result.") from None
    if not isinstance(payload, dict) or payload.get("success") is False or "error" in payload:
        raise ValueError("Ruflo refused the local task operation.")
    return payload


def coordinate(executable: Path, seal: str, review: dict, work: Path) -> dict:
    """Create, complete, and read back a local task carrying only evidence digests."""
    seal = _digest(seal)
    review_seal = _digest(review.get("review_sha256"))
    if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("Choose an approved absolute Ruflo executable.")
    state = work.resolve() / "ruflo"
    state.mkdir(mode=0o700)
    config = state / "config"
    # Ruflo falls back to the account's policy directory unless this XDG trust root exists.
    (config / "ruflo" / "policy-trust").mkdir(parents=True, mode=0o700)
    evidence = {"evidence_sha256": seal, "review_sha256": review_seal}
    node = shutil.which("node")
    path = os.pathsep.join((str(Path(node).parent), os.defpath)) if node else os.defpath
    env = {"PATH": path, "NODE_ENV": "production", "NO_COLOR": "1",
           "XDG_CONFIG_HOME": str(config)}
    with (state / "mcp.stderr").open("xb") as log, subprocess.Popen(
        [str(executable), "mcp", "start"], cwd=state, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
    ) as process, selectors.DefaultSelector() as stream:
        assert process.stdout is not None
        stream.register(process.stdout, selectors.EVENT_READ)
        pending = bytearray()
        request_id = 0

        def request(method: str, params: dict) -> dict:
            nonlocal request_id
            request_id += 1
            _send(process, {"id": request_id, "method": method, "params": params})
            return _response(process, stream, pending, request_id)

        def tool(name: str, arguments: dict) -> dict:
            return _tool_result(request("tools/call", {"name": name, "arguments": arguments}))

        try:
            initialized = request("initialize", {
                "protocolVersion": PROTOCOL, "capabilities": {},
                "clientInfo": {"name": "exoverse-review", "version": "1"},
            })
            server = initialized.get("serverInfo")
            if not isinstance(server, dict) or (server.get("name"), server.get("version")) != ("ruflo", SERVER_VERSION):
                raise ValueError(f"Use the qualified Ruflo MCP server version {SERVER_VERSION}.")
            _send(process, {"method": "notifications/initialized"})
            listed = request("tools/list", {}).get("tools")
            if not isinstance(listed, list) or not set(TOOLS) <= {
                item.get("name") for item in listed if isinstance(item, dict) and isinstance(item.get("name"), str)
            }:
                raise ValueError("The local Ruflo MCP server does not expose the required task tools.")
            created = tool("task_create", {
                "type": "research", "priority": "normal", "tags": ["exoverse", "local-review"],
                "description": f"Record local Exoverse review for evidence SHA-256 {seal}.",
            })
            task = created.get("taskId")
            if not isinstance(task, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", task):
                raise ValueError("Ruflo did not return a usable task identifier.")
            if created.get("status") != "pending":
                raise ValueError("Ruflo did not return a pending handoff.")
            with (state / "handoff.json").open("x", encoding="utf-8") as handle:
                json.dump({"task_id": task, **evidence}, handle, indent=2)
                handle.write("\n")
            finished = tool("task_complete", {"taskId": task, "result": evidence})
            observed = tool("task_status", {"taskId": task})
            if any(row.get("taskId") != task or row.get("status") != "completed"
                   for row in (finished, observed)) or observed.get("result") != evidence:
                raise ValueError("Ruflo did not read back the completed review and its evidence digests.")
            return {"task_id": task, "status": observed["status"], "server": {
                "name": server.get("name"), "version": server["version"],
            }, **evidence}
        finally:
            assert process.stdin is not None
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
