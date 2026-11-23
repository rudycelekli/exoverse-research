---
name: exoverse-research-workbench
description: Turn a new user's question into an offline Exoverse experiment, a reproducible result, and a paper draft. Use for research questions, measuring behavior, comparing variants, and evidence review.
---

# Research workbench

Ask what the researcher wants to learn and what they predict. For the first
study, use `exoverse_run_first_study` from the starter MCP server. It compares
an adaptive and an even-sampling strategy on a fixed simulated problem.
Explain what the result measured, and ask what variable they want to change.

For a question about exploration, agree on two exploration weights and the
predicted direction of expected reward loss. Call
`exoverse_run_local_comparison` with `question`, integer `baseline` and
`treatment` weights in hundredths, and `prediction` of `lower`, `higher`, or
`unchanged`. The result includes the matched runs, an evidence digest, and
a Markdown draft. Use the paired CLI for a two-file export. Keep the digest
separately and send the files to a reviewer who can use
`exoverse_verify_local_comparison` or `paired verify`.

For a question about incorrect completion reports, use
`exoverse_run_monitor_comparison`. Choose the `activity` and `ledger` signals,
and predict whether the treatment has `lower`, `higher` or `unchanged` false
alerts. Read both false alarms and missed detections, with their denominators.
The fixture checks fixed monitor rules. The shared paired verifier can replay
its study and report.

For other questions, identify the environment, the single proposed change,
the baseline, available evidence and the resolver for the outcome. Label
the design as planned until it has actually run. If the installed tools lack
the required adapter, say which input or operation is needed. Use the same
routine for application development: record one change, run the same checks
against a baseline, and retain failure evidence with the result.
