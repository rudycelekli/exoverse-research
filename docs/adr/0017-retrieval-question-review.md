# ADR 0017 — Show question-level retrieval evidence

## Context

Aggregate citation and abstention scores hide which questions each fallback
helps and which source spans a reviewer needs to inspect.

## Decision

Add question IDs, expected source spans or abstentions, arm submissions and
per-question outcomes to offline verification output. Derive them only after
the verifier has checked the retained artifacts and recomputed the scores.

## Alternatives

Embedding these rows into the original paper would change its canonical bytes.
Reviewers could inspect raw JSON files by hand, but would need to join labels
and answers themselves.

## Consequences

Earlier evidence and drafts keep their existing format. The JSON review exposes
the retained answer text, so apply the same sharing rules as the raw artifacts.

## Validation

Verify the real frozen-manifest run and confirm that question outcomes
reconstruct both arms' aggregate scores.
