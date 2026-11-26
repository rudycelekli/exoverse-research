# ADR 0018 — Discover every public Python qualification test

## Context

Directly executing a unittest module without a main entry point exits
successfully without running its tests. That happened with the project
module. The independent archive review exercised it through discovery.

## Decision

Use unittest discovery for the existing tests directory on both CI operating
systems. Keep shell replay and browser checks on their existing paths.

## Alternatives

Add a main block to each test file and retain a manual CI list. This adds
maintenance to every new test and leaves room for omissions.

## Consequences

Python test modules matching the repository naming convention run on both
hosted operating systems. Live provider and Docker evidence still require
separate qualification.

## Validation

Run the same discovery command locally and inspect the named project test
and total count. Verify the count on the hosted jobs before merge.
