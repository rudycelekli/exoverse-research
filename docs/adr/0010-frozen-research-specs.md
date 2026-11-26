# ADR 0010 — Freeze a study protocol before branching

## Context

A study needs to preserve its criteria and environment when a researcher tries
a different prompt, agent or harness. An independent researcher needs a way
to check that the recorded intervention changed one declared variable.

## Decision

Add a CLI that freezes a bounded JSON protocol, branches from a retained
parent fingerprint and verifies the resulting candidate independently.
A branch can replace exactly one member of the protocol's variables object.
The verifier reconstructs the expected candidate using the parent's full
protocol and compares canonical bytes.

## Alternatives

A free-form diff is useful for review but leaves the permitted change
ambiguous. A fixed list of eligible interventions constrains future
architectures and environment adapters.

## Consequences

The format admits structured interventions and fixes environment, rubric,
judge, seeds, budget and stopping rule across an immediate parent-child pair.
It verifies the declared change. Execution adapters must separately prove
they applied those exact inputs. Retain fingerprints independently and verify
each adjacent pair when reviewing a longer lineage.

## Validation

The CLI integration test freezes and branches from separate processes.
It verifies the branch, confirms the parent bytes stayed intact and rejects
a candidate with a modified rubric even when its fingerprint is updated.

Branching and verification require the exact canonical baseline bytes from
freeze. Duplicate JSON keys are refused before parsing can collapse them.
The regression checks that whitespace and a conflicting duplicate schema
cannot be accepted using the unchanged retained baseline fingerprint.
