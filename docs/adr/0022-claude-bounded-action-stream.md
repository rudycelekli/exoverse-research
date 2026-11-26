# ADR 0022 — Translate a bounded Claude Code action to structured output

## Context

Claude Code requests a stream and declares its StructuredOutput tool. In a
loopback test, one successful HTTP request yielded a CLI result with two
internal turns. The spend guard therefore counts actual upstream attempts.

## Decision

Share one-attempt turn state with the Codex bridge. Accept the expected
Messages route and a single StructuredOutput declaration. Reconstruct an
ordinary tool-free request from the coordinator's observation and let the
forwarding core enforce the output limit. Validate the provider's text
choice and encode it as a structured output event for the native client.

## Alternatives

Forwarding the original token limit, tool and control fields leaves the
upstream envelope dependent on CLI defaults. Returning a text-only stream
was tried offline and caused a second request without a structured result.

## Consequences

The module translates a single turn. Its synthetic stream counters are
placeholders. Reservations and provider receipts are separate. Authenticated
transport, gateway-only networking, and live billing remain qualification
steps. The existing host adapter is called separately from these bridges.

## Validation

Local tests assert only trusted inputs reach the gateway and duplicate
attempts and extra tools are refused. A real Claude Code loopback run used
one mocked upstream call with 32 output tokens enforced and produced the
expected structured action. No provider traffic was used.
