# ADR 0021 — Translate one Codex turn to a bounded action request

## Context

The installed CLI sends Responses streaming requests and advertises tools.
The existing Portkey core bounds non-streaming, text-only requests.

## Decision

Bind one bridge instance to one trusted workflow observation. Accept one
native streaming request for the pinned model, then construct a fresh
tool-free request from the coordinator observation. The forwarding core
reserves the request and sets the output limit. Validate the completed
response against the allowed choices before encoding Responses events for
the CLI. Refuse further attempts for the same observation.

## Alternatives

Forwarding native tool and conversation fields would grant the client
control of what the gateway sends. Streaming directly from the provider
would require auditing partial events and enforcing disconnect handling.

## Consequences

The bridge translates one action and buffers the bounded provider reply.
It needs an authenticated transport and sole egress before integrated
live use. The Claude protocol requires a separate adapter. Simulated
upstream replies provide no live provider or billing receipt.

## Validation

Local tests exercise tool stripping, trusted input, one-attempt limits and
rejection of unexpected tool output. A loopback fixture ran the installed
Codex CLI under an outbound-deny sandbox. The CLI consumed the bridge
stream, the mocked upstream saw one tool-free request capped at 32 output
tokens, and the structured action was saved. Zero provider calls.
