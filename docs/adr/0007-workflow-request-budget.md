# ADR 0007 — Reserve workflow gateway requests before forwarding

## Context

A workflow action invokes a native CLI. A single invocation can generate multiple HTTP requests. Counting actions alone cannot bound gateway spending. Both arms need to draw from a shared budget that survives process restarts.

## Decision

Add a local SQLite reservation ledger using integer millionths of a USD. Initialize it once with a total ceiling and request limit. Commit each priced upper bound before forwarding the request. SQLite serializes reservations across gateway workers. Duplicate request IDs and unavailable ledgers refuse the reservation. Holds remain charged against the ceiling for the duration of the pilot, including if a request fails after reservation.

## Alternatives

An in-memory counter resets on restart. Reserving per CLI invocation leaves its internal request count and cost uncontrolled. Billing reconciliation could reclaim unused holds but requires trusted provider receipts and falls outside this change.

## Consequences

The ledger supplies a reservation primitive. Native adapters do not yet use it. A live gateway must enforce a fixed provider and model, bound input and output costs, disable retries and fallbacks, and provide the only network route available to the containers. The gateway must supply a conservative price bound for each request. The pilot's credential, spend authorization, and raw evidence stay private.

## Validation

Offline tests exercise concurrent reservations, duplicate rejection, restart persistence, exhaustion of both limits, and a missing ledger. The existing scripted native CLI test exercises action parsing independently. This change has no paid traffic or live agent evidence.
