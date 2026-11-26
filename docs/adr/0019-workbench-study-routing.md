# ADR 0019 — Route installed research requests to the study CLI

## Context

Project, frozen protocol, and Harbor commands are shipped in the research
plugin. The installed workbench skill previously led the agent to the
starter, paired comparisons and generic simulations.

## Decision

Teach the existing skill when to select project, spec, and Harbor workflows.
Give the agent the cached plugin CLI path and fingerprint handoff rules.
Keep detailed command examples in the extracted package guide.

## Alternatives

Adding new MCP tools would change the tool surface and contract. Putting
all arguments into the skill would duplicate the CLI help and guide.

## Consequences

Agent hosts can discover the three workflows through the same installed skill.
The existing CLI retains responsibility for checking inputs and replaying
evidence. Agent selection behavior still needs a fresh-profile trial.

## Validation

Check the named routes against the shipped CLI help and qualify the next exact
ZIP in both fresh host profiles.
