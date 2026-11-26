# ADR 0005. Add native agent action selection to the public workflow runner

Status: Proposed

## Context

The public workflow interpreter compares predefined policies. Researchers also need their installed Claude Code and Codex CLIs to choose actions against the same workflow.

## Decision

Keep transition and reward logic in the deterministic interpreter. Select actions through bounded, structured requests to the two native CLIs, with distinct temporary working directories, ephemeral sessions, and tool restrictions. Require explicit model-call opt-in and cap the number of CLI invocations. Verify the returned action with the declared state transition table. Offline replay uses the saved actions and recomputes both traces.

## Alternatives

Direct tool access to the underlying host would expand the runtime and trust model. Copying the full private SDK would bring unrelated runtime dependencies. Static policies remain the zero-account control.

## Consequences

Live use requires separately configured agent credentials and may incur costs. The invocation cap is not a spend cap. The verifier establishes deterministic replay from recorded actions. Process-level container isolation and provider-authenticated evidence remain separate capabilities.

## Validation

Exercise both adapter contracts with offline stand-ins, enforce explicit opt-in, check identical criteria, and reject rehashed tampering. Use synthetic credential variables to check that each action-selection process receives only its own provider's variables and that version probes receive neither provider's variables. Check supported flags against the installed native CLI help. Live provider qualification requires an authorized route and budget.
