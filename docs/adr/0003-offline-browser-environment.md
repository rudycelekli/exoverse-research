# ADR 0003. Ship a self-contained browser environment

## Context

A first RL run should be possible from a downloaded source package without installing a model or starting a server.

## Decision

Provide a standalone HTML bandit environment. Compare two scripted policies on matched seeded reward streams. Export both traces and verify them by recomputation using the independently retained SHA-256 fingerprint.

## Alternatives

A local server could use the private engine directly but adds startup requirements. A screenshot would omit execution and replay.

## Consequences

The source package includes a browser-native reference environment with its own evidence schema. It demonstrates rollout and replay for one environment. The published 0.6.6 plugin ZIP has a separate inventory.

## Validation

The browser test opens the local HTML file with networking disabled, runs both policies, inspects 30 trace rows per arm, verifies a download in a fresh browser context, and rejects edited evidence with both the original and recalculated fingerprints.
