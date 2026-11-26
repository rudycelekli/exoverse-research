# ADR 0020 — Bind the reservation ledger to a frozen pilot

## Context

Opening a new ledger with the same ceiling would reset the accumulated
holds. A gateway restart also needs to use the same model prices, limits,
routes, and protocol fingerprint.

## Decision

Initialization returns a ledger identity and authorization fields for a
private receipt. A frozen-pilot gateway accepts the retained binding and
checks that its model policy and protocol reproduce the bound digest.
Each reservation transaction checks identity, ceiling, count limit, and
policy digest before accepting another hold.

## Alternatives

A filename alone cannot distinguish replacement databases. Checking the
policy only when constructing the gateway leaves later requests without
a check after the database changes.

## Consequences

Restarted workers can reuse the same binding and cannot silently accept a
new empty ledger or changed estimate. Keep the binding and database in a
trusted coordinator directory. Cloning or rolling back a valid database
remains outside this protection. Native adapters still need a sole gateway
network path, and provider billing and routes require live qualification.

## Validation

Offline tests simulate two restarts, cap exhaustion, an identically priced
replacement database, and changed prices. Verify refusals before transport.
