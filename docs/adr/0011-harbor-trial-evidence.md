# ADR 0011 — Verify Harbor trials with a frozen score rubric

## Context

A frozen intervention needs execution evidence and a reproducible evaluation.
Harbor stores per-trial results with an agent configuration, task checksum and
verifier rewards. A Harbor setup or execution failure must stay distinct from a
completed trial that earns a zero.

## Decision

Import two completed per-trial result files for a frozen agent-name branch.
Check their task identity and checksum, agent names, shared agent configuration
and environment settings. Apply the predeclared minimums to the named
verifier rewards. Preserve the input records and regenerate the scorecard from
them for offline verification and draft export.

## Alternatives

Importing a job average loses the trial identity and individual rubric
scores. Running Harbor from inside the importer would add engine setup and
credential requirements to offline verification.

## Consequences

This first contract supports one trial per arm. Seed 0 marks an unseeded
comparison. Raw imported trial records can contain local configuration and
should stay private until reviewed. Replay verifies arithmetic and consistency
against those records. It supplies no independent attestation of where a
trial executed. Judge status is explicit and judge output stays out of the
scorecard pending a live judge integration.

## Validation

Tests exercise independent CLI verification, successful and failing rubric
outcomes, rejection of a modified score even after rehashing, and refusal to
score a trial with an execution exception.
