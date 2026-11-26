"""Fixed-route Portkey forwarding for non-streaming workflow requests."""

from dataclasses import asdict, dataclass
import hashlib
import re
import json
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from workflow_request_budget import BudgetRefused, RequestBudget

PORTKEY = "https://api.portkey.ai/v1"
ROUTES = {
    "claude": ("@anthropic", "/messages", "max_tokens"),
    "codex": ("@openai", "/responses", "max_output_tokens"),
}
MAX_BODY_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
INPUT_FIELDS = {"claude": "messages", "codex": "input"}


def _text_messages(value):
    return isinstance(value, list) and bool(value) and all(
        isinstance(message, dict)
        and set(message) == {"role", "content"}
        and message["role"] in ("user", "assistant")
        and (
            isinstance(message["content"], str)
            or isinstance(message["content"], list) and all(
                isinstance(part, dict) and set(part) == {"type", "text"}
                and part["type"] in ("text", "input_text", "output_text") and isinstance(part["text"], str)
                for part in message["content"]
            )
        )
        for message in value
    )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


@dataclass(frozen=True)
class ModelPolicy:
    model: str
    context_tokens: int
    output_limit: int
    input_microusd_per_token: int
    output_microusd_per_token: int

    def __post_init__(self):
        limits = (self.context_tokens, self.output_limit, self.input_microusd_per_token,
                  self.output_microusd_per_token)
        if not self.model or any(type(value) is not int or value <= 0 for value in limits):
            raise ValueError("Model and positive integer limits and prices are required.")


def pilot_policy_sha256(protocol_sha256, models):
    if not isinstance(protocol_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", protocol_sha256):
        raise ValueError("Expected a retained frozen protocol fingerprint.")
    if set(models) != set(ROUTES) or not all(isinstance(model, ModelPolicy) for model in models.values()):
        raise ValueError("A fixed model policy is required for both agents.")
    policy = {"protocol_sha256": protocol_sha256, "gateway": PORTKEY, "routes": ROUTES,
              "models": {agent: asdict(model) for agent, model in models.items()}}
    raw = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class PortkeyGateway:
    def __init__(self, *, key, budget, models):
        if not isinstance(key, str) or not key or any(not 33 <= ord(char) <= 126 for char in key):
            raise ValueError("A scoped Portkey credential is required.")
        if set(models) != set(ROUTES):
            raise ValueError("A fixed model policy is required for both agents.")
        self._key = key
        self._budget = budget
        self._models = dict(models)
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    @classmethod
    def for_frozen_pilot(cls, *, key, ledger_path, binding, protocol_sha256, models):
        if binding.policy_sha256 != pilot_policy_sha256(protocol_sha256, models):
            raise BudgetRefused("The gateway model policy differs from the frozen pilot.")
        return cls(key=key, budget=RequestBudget(ledger_path, binding=binding), models=models)

    def forward(self, agent, path, body):
        """Reserve a conservative hold, then make one upstream attempt."""
        if agent not in ROUTES:
            raise BudgetRefused("Unknown workflow agent.")
        provider, endpoint, token_field = ROUTES[agent]
        if path != endpoint or not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
            raise BudgetRefused("Unsupported workflow request.")
        try:
            payload = json.loads(body)
        except (ValueError, RecursionError) as error:
            raise BudgetRefused("Invalid workflow request JSON.") from error
        policy = self._models[agent]
        input_field = INPUT_FIELDS[agent]
        instruction_field = "system" if agent == "claude" else "instructions"
        allowed_fields = {"model", "stream", token_field, input_field, instruction_field}
        if (not isinstance(payload, dict) or payload.get("model") != policy.model
                or payload.get("stream", False) is not False
                or set(payload) - allowed_fields
                or not isinstance(payload.get(instruction_field, ""), str)):
            raise BudgetRefused("Request does not match the fixed workflow model policy.")
        input_value = payload.get(input_field)
        if not (_text_messages(input_value) or agent == "codex" and isinstance(input_value, str)):
            raise BudgetRefused("Request does not match the fixed workflow model policy.")
        tokens = payload.get(token_field, policy.output_limit)
        if type(tokens) is not int or not 1 <= tokens <= policy.output_limit:
            raise BudgetRefused("Request exceeds the workflow output limit.")
        payload[token_field] = tokens
        if agent == "codex":
            payload["store"] = False
        headers = {
            "Content-Type": "application/json",
            "x-portkey-api-key": self._key,
            "x-portkey-provider": provider,
        }
        if agent == "claude":
            headers["anthropic-version"] = "2023-06-01"
        request = Request(PORTKEY + endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
        hold = policy.context_tokens * policy.input_microusd_per_token + tokens * policy.output_microusd_per_token
        self._budget.reserve(uuid4().hex, hold)
        try:
            with self._opener.open(request, timeout=60) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except (URLError, OSError):
            raise ValueError("Portkey request failed. The reservation remains held.") from None
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Portkey response exceeded the workflow size limit.")
        return data
