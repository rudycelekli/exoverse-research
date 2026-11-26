# ADR 0006. Evaluate workflow criteria and replay in a pinned offline container

Status: Proposed

## Context

A terminal success state does not prove that an agent complied with the workflow. Researchers also need an offline runtime for scoring and independent reproduction.

## Decision

Support optional required and forbidden states. Record a per-arm breakdown when state criteria are supplied, and preserve existing receipt bytes for workflows with the original criteria. Provide a Docker wrapper that accepts only an existing immutable image ID, mounts a single input and the runtime read-only, and disables networking.

## Alternatives

An open-ended judge is useful for qualitative criteria but needs calibration and separate evidence. Mounting the full project would expose unrelated data. A mutable image tag would weaken the execution receipt.

## Consequences

Users can distinguish a goal reached through the required procedure from an identical outcome reached by skipping review. The container supports scripted comparisons and offline replay. Provider-backed native agent execution requires its own authorized model route, budget and isolation design.

## Validation

Replay a two-policy workflow whose arms both reach the goal but differ on the required procedure. Verify out of process with no network and reject modified evidence even when its checksum is recomputed.
