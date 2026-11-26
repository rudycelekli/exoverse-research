# ADR 0023 — Authenticate each native turn on loopback

## Context

Each native stream bridge needs a local HTTP boundary. A listening endpoint
must require the token of the turn it serves before passing any request to
the bridge.

## Decision

Use an ephemeral IPv4 loopback listener per turn. Generate a random token,
accept the native client authentication header for that turn, and reject
duplicate or oversized body lengths before invoking the stream bridge.
Return only fixed errors to the client and omit request logs.

## Alternatives

A process-global endpoint would need a separate routing and authorization
table. Reusing the upstream credential across both sides would expose it
to the native client.

## Consequences

The local turn endpoint does not itself enforce host or container egress.
The coordinator owns the bridge and bounds upstream execution. The
listener is intended for a local sandboxed CLI, with a socket idle timeout.

## Validation

Unit tests confirm invalid credentials and oversized payloads reach no
bridge. A deny-egress loopback fixture used real Claude Code and Codex
with fresh homes and separate tokens. Both returned validated actions.
The bound shared ledger recorded both mocked calls and hit the fixture
ceiling. No provider traffic was used.
