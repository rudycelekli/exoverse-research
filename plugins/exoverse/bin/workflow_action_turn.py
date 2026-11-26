"""Shared one-attempt turn state for bounded workflow bridges."""

import json
from threading import Lock

from workflow_portkey import MAX_BODY_BYTES
from workflow_request_budget import BudgetRefused

INSTRUCTION = 'Choose one allowed action. Return only JSON of the form {"action":"..."}.'


class ActionTurn:
    def __init__(self, gateway, model, observation):
        self.gateway = gateway
        self.model = model
        self.allowed = tuple(observation["allowed_actions"])
        self.input = json.dumps(observation, sort_keys=True)
        self._lock = Lock()
        self._attempted = False

    def begin(self, path, accepted_paths, body):
        if path not in accepted_paths or not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
            raise BudgetRefused("Unsupported native workflow request.")
        try:
            request = json.loads(body)
        except (ValueError, RecursionError):
            raise BudgetRefused("Invalid native workflow request JSON.") from None
        if (not isinstance(request, dict) or request.get("stream") is not True
                or request.get("model") != self.model):
            raise BudgetRefused("The native workflow requires the pinned streaming model.")
        return request

    def forward(self, agent, path, **fields):
        with self._lock:
            if self._attempted:
                raise BudgetRefused("This workflow turn already attempted a provider request.")
            self._attempted = True
        return self.gateway.forward(agent, path, json.dumps({"model": self.model, **fields}).encode())

    def action(self, text):
        action = json.loads(text)
        if not isinstance(action, dict) or set(action) != {"action"} or action["action"] not in self.allowed:
            raise ValueError("Provider returned an action outside the trusted observation.")
        return action
