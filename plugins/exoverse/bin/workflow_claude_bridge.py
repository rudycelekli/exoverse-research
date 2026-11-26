"""Translate one trusted workflow turn into Claude Code structured-output events."""

import json

from workflow_action_turn import ActionTurn, INSTRUCTION
from workflow_request_budget import BudgetRefused

MESSAGES_PATHS = ("/v1/messages", "/v1/messages?beta=true")


def _events(model, action):
    # These counters are client-facing placeholders for the synthetic stream.
    # The upstream reservation is retained independently.
    usage = {"input_tokens": 0, "output_tokens": 0,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    events = (
        ("message_start", {"message": {
            "id": "msg_workflow", "type": "message", "role": "assistant", "content": [],
            "model": model, "stop_reason": None, "stop_sequence": None, "usage": usage,
        }}),
        ("content_block_start", {"index": 0, "content_block": {
            "type": "tool_use", "id": "toolu_workflow", "name": "StructuredOutput", "input": {},
        }}),
        ("content_block_delta", {"index": 0, "delta": {
            "type": "input_json_delta", "partial_json": json.dumps(action, separators=(",", ":")),
        }}),
        ("content_block_stop", {"index": 0}),
        ("message_delta", {"delta": {"stop_reason": "tool_use", "stop_sequence": None},
                           "usage": {"output_tokens": 0}}),
        ("message_stop", {}),
    )
    return b"".join(
        f"event: {kind}\ndata: ".encode() + json.dumps({"type": kind, **data}).encode() + b"\n\n"
        for kind, data in events
    )


class ClaudeActionBridge:
    def __init__(self, gateway, model, observation):
        self._turn = ActionTurn(gateway, model, observation)

    def respond(self, path, body):
        request = self._turn.begin(path, MESSAGES_PATHS, body)
        tools = request.get("tools")
        if (not isinstance(tools, list) or len(tools) != 1
                or not isinstance(tools[0], dict) or tools[0].get("name") != "StructuredOutput"):
            raise BudgetRefused("Claude workflow requires only its structured output tool.")
        raw = self._turn.forward("claude", "/messages",
                                 system=INSTRUCTION, messages=[{"role": "user", "content": self._turn.input}])
        try:
            response = json.loads(raw)
            content = response["content"]
            if response["stop_reason"] != "end_turn" or len(content) != 1 or content[0]["type"] != "text":
                raise ValueError("Provider did not return one completed text action.")
            action = self._turn.action(content[0]["text"])
        except (ValueError, KeyError, IndexError, TypeError, RecursionError):
            raise ValueError("Provider did not return a valid completed workflow action.") from None
        return _events(self._turn.model, action)
