# Public browser and workflow release wave

Scope is public main at `7d3b23a05f02728b5fa5ea601511d58faa8e614d`.

- The independent browser reviewer reproduced a deterministic offline bandit
  with 30 steps per arm. A separate browser context verified the export and
  rejected changed traces with either original or recomputed fingerprints.
  Hosted macOS and Ubuntu browser checks passed before merge.
- The independent workflow reviewer ran four tests from a fresh source
  archive, exercised the no-prediction starter, paired verification and local
  review, and rejected an edited scored paper. All five hosted PR checks passed.
- The merged main qualification and replay jobs passed. These are source
  and synthetic research checks. Live agent results and time to first study
  for an unaided researcher remain unmeasured.

[Browser PR](https://github.com/rudycelekli/exoverse-research/pull/3) ·
[Workflow PR](https://github.com/rudycelekli/exoverse-research/pull/4) ·
[Main qualification](https://github.com/rudycelekli/exoverse-research/actions/runs/45788775518)
