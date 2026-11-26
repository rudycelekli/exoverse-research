# ADR 0015 — Retain the inputs used by both retrieval arms

## Context

A reviewer may open a later checkout where the corpus or labels have changed.
The existing verifier binds answers and receipts but relies on the checkout for
all evaluation inputs.

## Decision

Copy the fixed task files into the run directory before freezing the protocol.
Pass that task to Harbor for both arms. Keep the SHA-256 of each input in the
review receipt and refuse to export if inputs change during execution. During
offline review, rescore the raw answers using retained corpus and labels after
checking every retained input. Run the scorer from the trusted checkout after
checking that it matches the recorded scorer.

## Alternatives

A Git commit alone ties the result to a repository and requires access to the
original revision. Executing code from the received archive gives that archive
control of the verifier process.

## Consequences

New runs carry their questions, labels, corpus and other task inputs alongside
the result. Earlier receipts remain readable and report that inputs were not
independently fingerprinted. This verifies file bytes and recorded scores.
Rebuilding the Docker runtime still depends on the resolved base image.

## Validation

Run both Harbor arms using the snapshot. Replay the retained run offline,
then change a question in a scratch copy and confirm verification fails.
Also check that the previous receipt still verifies.
