"""Translate one trusted workflow turn into a bounded Codex Responses stream."""

import json
from threading import Lock

from workflow_portkey import MAX_BODY_BYTES
from workflow_request_budget import BudgetRefused

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


def _read_action(raw, allowed):
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
        action = json.loads(content[0]["text"])
        if not isinstance(action, dict) or set(action) != {"action"} or action["action"] not in allowed:
            raise ValueError("Provider returned an action outside the trusted observation.")
        response_id = response["id"]
        if not isinstance(response_id, str) or not 0 < len(response_id) <= 128:
            raise ValueError("Provider response identity is invalid.")
        return response_id, action, response.get("usage")
    except (ValueError, KeyError, TypeError, RecursionError):
        raise ValueError("Provider did not return a valid completed workflow action.") from None


class CodexActionBridge:
    """A single sequential action bound to the coordinator's trusted observation."""

    def __init__(self, gateway, model, observation):
        self._gateway = gateway
        self._model = model
        self._allowed = tuple(observation["allowed_actions"])
        self._input = json.dumps(observation, sort_keys=True)
        self._lock = Lock()
        self._attempted = False

    def respond(self, path, body):
        if path != RESPONSES_PATH or not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
            raise BudgetRefused("Unsupported Codex workflow request.")
        try:
            request = json.loads(body)
        except (ValueError, RecursionError):
            raise BudgetRefused("Invalid Codex workflow request JSON.") from None
        if (not isinstance(request, dict) or request.get("stream") is not True
                or request.get("model") != self._model):
            raise BudgetRefused("Codex workflow requires the pinned streaming model.")
        with self._lock:
            if self._attempted:
                raise BudgetRefused("This workflow turn already attempted a provider request.")
            self._attempted = True
        # The coordinator owns the observation. Native tool declarations and
        # conversation history are deliberately excluded from the billable request.
        request = {"model": self._model, "input": self._input,
                   "instructions": 'Choose one allowed action. Return only JSON of the form {"action":"..."}.'}
        upstream = self._gateway.forward("codex", "/responses", json.dumps(request).encode())
        response_id, action, usage = _read_action(upstream, self._allowed)
        return _encode_events(response_id, self._model, action, usage)
