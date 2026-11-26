# ADR 0002. Run public first-study qualification on clean runners

## Context

The release and guide have been tested in fresh host profiles. Routine source changes need a repeatable check of the documented workflows and evidence verifier across operating systems.

## Decision

Run standard-library integration tests and the alignment example in GitHub Actions on Linux and macOS. Exercise the shipped CLI and MCP server with fixed public cases. Check that a skipped or different starter expectation leaves measurements intact, that an exported study and draft replay in a second workspace, and that the verifier rejects an edited draft and a wrong fingerprint.

## Alternatives

Unit tests would leave the executable entry points untested. Requiring both paid hosts in every CI job would introduce sign-in and service dependencies. Keep host installation and interactive onboarding as separate qualifications.

## Consequences

The workflow uses read-only repository permissions and requires no provider credentials. The fixed fingerprint catches changes in the public reference experiment. An intentional change to that experiment requires updating its evidence and documentation. These checks cover the public checkout's offline CLI and MCP server.

## Validation

All three integration tests passed locally on macOS with Python 3.9.6. Hosted results are tracked on the pull request.
