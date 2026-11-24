# ADR 0008 — Reserve fixed-route Portkey requests

## Context

The reservation ledger needs a transport that applies one shared ceiling to both
workflow arms before authenticated upstream requests.

## Decision

Add a forwarding core with fixed Portkey URLs and provider routes. Accept bounded,
non-streaming text requests for configured models. Reserve the cost of the full
configured context plus the enforced output limit before forwarding. Round rates
up to integer millionths of a USD per token when creating a model policy.
A failed transport attempt retains its hold. The HTTP client performs no retries,
redirects, or environment-proxy discovery.

## Alternatives

Forwarding arbitrary request bodies leaves pricing and routing open to client
control. Estimating input usage from string length relies on provider-specific
tokenization. Reserving against the provider's configured hard context limit
avoids that estimate and can over-reserve on short requests.

## Consequences

The core is for offline contract testing until exact provider models, hard
limits, highest applicable rates, and integration retry/fallback policies are
verified. A native adapter bridge still needs to handle each CLI's wire protocol
and provide its sole reachable network path from its container. Streaming and
native structured-output requests are currently outside the supported contract.

## Validation

A mocked transport test exercises both provider routes against a single $200
fixture budget. It confirms a third request is blocked before transport when two
reservations consume the ceiling. Wrong endpoints, model overrides and streaming
requests are blocked. No provider traffic is used by the test.
