# ADR 0009 — Local research projects with replay-backed drafts

## Context

Individual workflows produce evidence, but researchers need a persistent home for
their question and related studies. A draft should be reproducible from that
evidence after a restart.

## Decision

Add a CLI project backed by one local SQLite file. Retain offline workflow
evidence under its content digest. Recompute every stored result before
exporting a Markdown draft. Use the existing workflow engine for execution and
verification.

## Alternatives

A directory of loosely related outputs is portable but requires manual record
keeping. A hosted database enables team collaboration but adds setup and a
network dependency to the first study.

## Consequences

Project storage is portable and supports repeated workflow runs. The current
draft is a research worksheet with replayed results. Versioned protocols,
branch lineage, Harbor environments, live runs and judge evaluation remain
future integrations.

## Validation

The CLI can create a project, record a workflow and export a replayed draft from
separate processes. The project test exercises deduplication and refuses a draft
after the stored evidence changes.
