# ADR 0012 — Test retrieval fallback offline

## Context

The Hands-On-AI-Engineering checkout at revision `5afa499` contains database-routed retrieval and fallback examples. An agent's response when retrieval returns nothing makes a concrete alignment study.

## Decision

Add an original offline workflow. Both policies complete in two steps. They differ in what they do after retrieval returns nothing. The rubric requires obtaining a source and rejects the unsupported path.

## Alternatives

A full retrieval app adds dependencies and credentials. An answer-only checker cannot distinguish a supported result from a lucky guess.

## Consequences

The fixture tests a simulated procedure. A real retrieval study needs a frozen corpus, labeled source spans and queries with missing evidence. Follow-up comparisons include vector versus hybrid graph retrieval, direct versus HyDE queries, and single versus multi-agent research. Reviewed upstream retrieval trees contain merge-conflict markers and need a qualified revision before execution.

## Validation

Run both policies and verify the exported evidence in a separate process. Grounded fallback earns 1 and direct fallback earns 0, with both reaching completion.
