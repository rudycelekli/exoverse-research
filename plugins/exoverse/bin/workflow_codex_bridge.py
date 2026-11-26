"""Translate one trusted workflow turn into a bounded Codex Responses stream."""

import json
from workflow_action_turn import ActionTurn, INSTRUCTION

RESPONSES_PATH = "/v1/responses"


def _encode_events(response_id, model, action, usage):
    answer = json.dumps(action, separators=(",", ":"))
    item = {"id": "msg_workflow", "type": "message", "role": "assistant",
            "status": "completed", "content": [
                {"type": "output_text", "text": answer, "annotations": []},
            ]}
    response = {"id": response_id, "object": "response", "created_at": 0, "model": model,
                "status": "in_progress", "output": []}
    completed = {**response, "status": "completed", "output": [item]}
    if usage is not None:
        completed["usage"] = usage
    events = (
        ("response.created", {"response": response}),
        ("response.output_item.added", {"output_index": 0,
                                       "item": {**item, "status": "in_progress", "content": []}}),
        ("response.output_text.delta", {"item_id": item["id"], "output_index": 0,
                                        "content_index": 0, "delta": answer}),
        ("response.output_item.done", {"output_index": 0, "item": item}),
        ("response.completed", {"response": completed}),
    )
    return b"".join(
        f"event: {kind}\ndata: ".encode()
        + json.dumps({"type": kind, "sequence_number": index, **data}).encode()
        + b"\n\n"
        for index, (kind, data) in enumerate(events)
    )


def _read_action(raw, turn):
    try:
        response = json.loads(raw)
        if response["status"] != "completed":
            raise ValueError("Provider did not complete the workflow turn.")
        messages = [item for item in response["output"] if item["type"] == "message"]
        if len(messages) != 1 or any(item["type"] not in {"message", "reasoning"} for item in response["output"]):
            raise ValueError("Provider emitted an unexpected tool or output item.")
        content = messages[0]["content"]
        if len(content) != 1 or content[0]["type"] != "output_text":
            raise ValueError("Provider did not return one text action.")
        action = turn.action(content[0]["text"])
        response_id = response["id"]
        if not isinstance(response_id, str) or not 0 < len(response_id) <= 128:
            raise ValueError("Provider response identity is invalid.")
        return response_id, action, response.get("usage")
    except (ValueError, KeyError, TypeError, RecursionError):
        raise ValueError("Provider did not return a valid completed workflow action.") from None


class CodexActionBridge:
    """A single sequential action bound to the coordinator's trusted observation."""

    def __init__(self, gateway, model, observation):
        self._turn = ActionTurn(gateway, model, observation)

    def respond(self, path, body):
        self._turn.begin(path, (RESPONSES_PATH,), body)
        # Only the coordinator's observation is included in the upstream turn.
        upstream = self._turn.forward("codex", "/responses", input=self._turn.input,
                                      instructions=INSTRUCTION)
        response_id, action, usage = _read_action(upstream, self._turn)
        return _encode_events(response_id, self._turn.model, action, usage)
