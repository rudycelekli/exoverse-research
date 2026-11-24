"""Action-only native CLI adapters for a declarative workflow environment."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

SCHEMA = {"type": "object", "properties": {"action": {"type": "string"}},
          "required": ["action"], "additionalProperties": False}
PROMPT = "Choose one allowed action for this observation. Return only the action JSON. Do not use tools."


def _call(args, work, env, prompt=None):
    with tempfile.TemporaryFile() as stdout:
        with subprocess.Popen(args, cwd=work, env=env, stdout=stdout, stderr=subprocess.DEVNULL,
                              stdin=subprocess.PIPE if prompt else subprocess.DEVNULL,
                              start_new_session=True) as process:
            try:
                process.communicate(input=prompt.encode() if prompt else None, timeout=90)
            except subprocess.TimeoutExpired as error:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise ValueError("Agent timed out. No experiment score was saved.") from error
            if process.returncode:
                raise ValueError("Agent exited unsuccessfully. Check its authentication and supported CLI version.")
        stdout.seek(0)
        raw = stdout.read(65537)
    if len(raw) > 65536:
        raise ValueError("Agent result exceeds the protocol size limit.")
    return raw.decode()


def connector(host, work):
    executable = shutil.which(host)
    if not executable:
        raise ValueError(f"Install and authenticate {host} before running a live workflow.")
    keys = ("PATH", "HOME", "CODEX_HOME", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "TMPDIR", "CLAUDE_CODE_OAUTH_TOKEN")
    env = {key: os.environ[key] for key in keys if key in os.environ}
    env.update(DISABLE_TELEMETRY="1", CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
    version = _call([executable, "--version"], work, env).strip()
    if not version or len(version) > 160:
        raise ValueError("Agent version could not be identified.")
    schema = work / "action.schema.json"
    schema.write_text(json.dumps(SCHEMA))

    def choose(observation):
        prompt = PROMPT + "\n" + json.dumps(observation, sort_keys=True)
        if host == "claude":
            args = [executable, "-p", "--bare", "--tools", "", "--strict-mcp-config",
                    "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence",
                    "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
            response = json.loads(_call(args, work, env, prompt))
            if response.get("is_error") or response.get("num_turns") != 1:
                raise ValueError("Claude Code did not return a successful single-turn result.")
            action = response.get("structured_output")
        else:
            outfile = work / "action.json"
            outfile.unlink(missing_ok=True)
            args = [executable, "-a", "never", "--disable", "shell_tool", "--disable", "unified_exec",
                    "-c", 'web_search="disabled"', "exec", "--ignore-user-config", "--ignore-rules",
                    "--sandbox", "read-only", "--ephemeral", "--skip-git-repo-check",
                    "--output-schema", str(schema), "--output-last-message", str(outfile), "-"]
            _call(args, work, env, prompt)
            if not outfile.is_file() or outfile.stat().st_size > 4096:
                raise ValueError("Codex did not return a bounded action.")
            action = json.loads(outfile.read_bytes())
        if not isinstance(action, dict) or set(action) != {"action"} or action["action"] not in observation["allowed_actions"]:
            raise ValueError("Agent returned an action outside the allowed workflow choices.")
        return action["action"]

    return choose, version
