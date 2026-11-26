# ADR 0004. Bring local study tools and workflow comparison into the public candidate

## Context

Public 0.6.6 can create and verify reference studies. Researchers need to analyze their own observations and model answers, and turn simple workflows into experiments.

## Decision

Port the standalone private study tools through commit bb9c7eade9d7724c8464237c5174b721bb5d892c. Add a finite-state workflow runner for two explicit policies and a researcher-defined terminal goal and deadline. Keep execution in the existing standalone launcher and export a fingerprinted replayable trace.

## Alternatives

Running arbitrary scripts would require a separate sandbox, dependencies and an external agent contract. A prompt-only comparison would omit state transitions and workflow termination.

## Consequences

The imported tools provide scoring, local collection and bundled verification. Model-backed collection requires existing Ollama and weights. Workflow comparisons require no model and isolate state per episode. They execute only declared transitions and do not provide process isolation for external programs.

## Validation

Fresh extracted artifacts exercise the licensed package, compare two policies under a user-specified criterion, reject edited evidence, and retain compatibility with the public starter flow.
