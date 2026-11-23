# ADR 0001. Replay a complete alignment study from the public checkout

## Context

A researcher should be able to see how Exoverse goes from a question to auditable evidence before installing a plugin or signing in to an agent. The public plugin already has a deterministic monitor comparison, paper export, and verifier.

## Decision

Use those released commands in a shell example. Run the same comparison into two independent directories. Verify each against the fingerprint from the qualified monitor study and check that both exported files match byte for byte. Use the same fixture in the README to explain what the result measures.

## Alternatives

A screenshot would show the results but give readers no way to verify them. An agent-only walkthrough would demonstrate agent integration but require an installation and possibly a host login. Building another demo runner would duplicate the released study and verifier.

## Consequences

The example requires a checkout, a POSIX shell, and Python 3.9 or newer. It leaves both bundles on disk so the researcher can inspect them. The example is a calibration on eight scripted cases. The ledger rule and the ground truth use the same completion record. Changing the study inputs or fixture requires a new measurement and corresponding fingerprint. The example lives at the repository root alongside the docs, outside the released plugin.

## Validation

The example passed on macOS with Python 3.9.6 from an exported source checkout. Both the source and output paths contained spaces. An outbound socket probe was denied. The example verified eight paired cases, reproduced both files byte for byte, and made zero model calls. The README counts matched the generated paper. The verifier rejected an edited copy of that paper.
