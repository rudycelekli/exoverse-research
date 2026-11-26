# ADR 0016 — Freeze the input manifest before Harbor execution

## Context

The retrieval review receipt records the individual task file fingerprints.
Researchers also need to verify that the receipt reflects the input manifest
committed to by the baseline and inherited by the candidate.

## Decision

Hash the canonical map of task paths to SHA-256 fingerprints. Store that digest
in the Harbor environment of the frozen baseline, before running either arm.
The verifier recomputes the manifest digest from the receipt and compares it
with the baseline, then checks each retained file and rescores the answers.

## Alternatives

The Harbor task checksum alone would require a Harbor installation or a second
implementation of its directory hashing algorithm to verify retained inputs.
Binding only the review receipt leaves the pre-run protocol without an offline
commitment to the individual file hashes.

## Consequences

Both arms share an input commitment that standard Python can check. Older
bundles keep their earlier guarantees and explicitly report that this
commitment is absent. The verification still depends on independently
retained fingerprints and trusted verifier code.

## Validation

Verify a fresh two-arm Harbor run and a historical run. Rewrite a manifest
entry in a copy of the receipt, retain the evidence fingerprint and supply
the recomputed receipt fingerprint. The verifier must reject the mismatch
against the frozen baseline.
