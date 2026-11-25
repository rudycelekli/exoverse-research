# ADR 0013 — Score retrieval fallback on a frozen Harbor corpus

## Context

The finite-state retrieval example verifies workflow semantics. A Harbor
study needs actual source records, questions and independently scored outputs.

## Decision

Package a synthetic corpus and five questions in one Harbor task. Use three
answerable and two unanswerable cases. Hold the initial retrieval and corpus
fixed. Direct fallback answers from its default when retrieval fails.
Grounded fallback searches for matching evidence and abstains on a miss.
Keep the labels with the verifier and score exact citation-and-answer support
and justified abstention independently. Freeze the Harbor task checksum and
agent branch before execution. Replay the answer score on the host and verify
the imported Harbor bundle before exporting the draft.

## Alternatives

An AI judge can handle free-form equivalence but introduces calibration and
provider requirements. A deterministic scorer makes this first small corpus
reproducible and exposes exactly what passed.

## Consequences

The study measures scripted policies on a deliberately small synthetic corpus.
It does not estimate general retrieval performance. Custom Harbor agents are
bound by name and import path in the frozen intervention. Harbor's task
checksum is used for compatibility with the existing trial importer.

## Validation

The runner verifies that both offline answer scores equal their corresponding
Harbor rewards before exporting the draft. See the study guide for the run and
verification commands.

On 2026-11-24, Harbor 0.25.0 and Docker 29.9.3 ran both frozen arms, with
zero trial exceptions. Direct fallback scored 1/3 for citation support and
0/2 for abstention. Grounded fallback scored 3/3 and 2/2 respectively.
Both Harbor scores matched local rescoring of the answers. A new CLI process
verified the retained evidence fingerprint and reproduced a byte-identical
draft. Evidence SHA-256
`71eaca6026b6083f6d7a94fe95bacb5c67ce4e23bd0ba79bd06c48e17ff2fa99`.
