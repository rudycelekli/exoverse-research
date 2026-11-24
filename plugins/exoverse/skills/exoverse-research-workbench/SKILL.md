---
name: exoverse-research-workbench
description: Turn a new user's question into an offline Exoverse experiment, a reproducible result, and a paper draft. Use for research questions, measuring behavior, comparing variants, and evidence review.
---

# Research workbench

Ask what the researcher wants to learn. Explain that a pre-run guess is optional for the starter. For the first
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
`exoverse_verify_local_comparison` or `paired verify`. To verify and regenerate
both files locally, use `paired reproduce SOURCE --sha256 ORIGINAL_FINGERPRINT --out NEW_FOLDER`.
Use the folder as SOURCE to also check the supplied paper. With only
`study.json` as SOURCE, say that the paper was regenerated from the evidence.

For a question about incorrect completion reports, use
`exoverse_run_monitor_comparison`. Choose the `activity` and `ledger` signals,
and predict whether the treatment has `lower`, `higher` or `unchanged` false
alerts. Read both false alarms and missed detections, with their denominators.
The fixture checks fixed monitor rules. The shared paired verifier can replay
its study and report.

For results the researcher already collected, ask for matched case IDs,
the common metric and units, and two arm labels. Use
`exoverse_analyze_paired_outcomes` with rows containing `case_id`, integer
`baseline`, and integer `treatment`. Use `paired analyze` on a local CSV
with those headers to save the receipt and draft. Explain the measured
differences and that replay verifies the analysis of supplied scores.

For exact-answer evaluation, create the reference key with
`exoverse_create_answer_key` and have the researcher retain its fingerprint
before collecting answers. Give both settings the same cases. Then use
`exoverse_score_paired_answers` with the saved key, fingerprint, arm labels,
and one baseline and treatment answer per case. The CLI equivalents are
`paired key` and `paired score`. Explain the exact-match rule and the limits
of replaying scores from answer hashes.

For a small model-backed comparison, if the researcher has a trusted local
Ollama service and existing weights, use `exoverse-plugin experiment run`
with a case list and the retained key fingerprint. Keep the model and
cases fixed and vary only the system prompt. If the collection is
incomplete, report an execution failure. Give the researcher the experiment
fingerprint and confirm `experiment verify` in a second project. Keep
prompts and raw responses local by default.

For other questions, identify the environment, the single proposed change,
the baseline, available evidence and the resolver for the outcome. Label
the design as planned until it has actually run. If the installed tools lack
the required adapter, say which input or operation is needed. Use the same
routine for application development: record one change, run the same checks
against a baseline, and retain failure evidence with the result.

For a workflow simulation, ask for the initial state, allowed actions,
destination states, terminal goal and deadline. Ask for the choices of
two scripted policies. Use `exoverse-plugin workflow run` to record both
runs, then `workflow verify` with the original fingerprint. Explain that
the result measures the declared workflow simulation.
