# ADR 0014 — Verify retrieval study artifacts without Harbor

## Context

A reviewer needs a repeatable check for the raw answers, Harbor results and
draft. Checking only the evidence bundle leaves the raw answers outside the
verification boundary.

## Decision

Add an offline mode to the retrieval runner. Require separately retained
fingerprints for the evidence and verification receipt. Match the raw Harbor
records to the bundle, rescore the retained answers, check their fingerprints
and compare the draft byte for byte with a replay.

## Alternatives

Manual commands can replay each score but leave cross-artifact comparisons to
the reviewer. A signed archive would add distribution and identity management.

## Consequences

Review requires the same trusted source revision for the scorer and labels.
A verified bundle establishes artifact consistency. The review does not
re-execute either policy or attest to who ran Harbor.

## Validation

Verify the retained real Harbor run through the new command. In a scratch
copy, change an already-wrong answer without changing the expected reward
and confirm the raw answer fingerprint blocks verification.
