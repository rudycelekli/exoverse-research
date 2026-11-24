# Research projects

Use one project database per research question. These commands work offline
from the package checkout and use the same workflow engine as a standalone study.

```sh
python3 plugins/exoverse/bin/exoverse-plugin project review.sqlite init --question "Does the review policy meet the procedure?"
python3 plugins/exoverse/bin/exoverse-plugin project review.sqlite run examples/review-workflow.json
python3 plugins/exoverse/bin/exoverse-plugin project review.sqlite list
python3 plugins/exoverse/bin/exoverse-plugin project review.sqlite draft paper.md
```

Run additional workflow files against the same project to collect more results.
An identical result is stored once. A draft includes fingerprints, methods,
replayed episode results and limitations. Preserve the project database with
the draft so another researcher can rerun the export.

## Research protocol and branching

The next version should freeze the question, hypothesis, baseline, changed
variable, task versions, seeds, criteria, budget and stopping rule before a run.
A branch should retain the parent's protocol fingerprint and record the changed
fields. Compare runs against their frozen protocols so an edit never rewrites
earlier evidence.

Harbor tasks should use the same environment interface as local workflows.
Pin task and runtime revisions, record isolation and distinguish infrastructure
failures from scores. For alignment studies, capture allowed actions,
undesirable trajectories and positive and negative controls. Score deterministic
rules first. Where a rubric needs judgment, version the judge and rubric,
blind arm labels, calibrate against human examples and allow abstention.
A paper export should cite the evidence behind every reported result and show
sample counts, failures, uncertainty and the limits of the design.

## Freeze and verify a branch

Use a JSON protocol with `question`, `hypothesis`, `environment`, `rubric`,
`judge`, `seeds`, `budget_microusd`, `stopping_rule` and `variables`.
Use a judge object describing the intended evaluator, or null for a
deterministic-only study. Put the intervention in a named member of
`variables`. For example, a memory architecture can be a single structured
variable. Prespecify smaller ablations if the combination wins.

```sh
exoverse-plugin spec freeze protocol.json --out baseline.json
exoverse-plugin spec branch baseline.json prompt new-prompt.json \
  --parent-sha256 "$baseline_sha" --out candidate.json
exoverse-plugin spec verify baseline.json candidate.json \
  --parent-sha256 "$baseline_sha" --candidate-sha256 "$candidate_sha"
```

Take the hash values from the corresponding commands and keep them with the
study record. The replacement file contains the new JSON value for the
variable. An independent agent can run the last command with the artifacts
and the retained fingerprints. This checks protocol lineage. Harbor and judge
execution receipts are separate integrations.

## From prior work to a new method

- Extract a paper's method and assumptions, then reproduce an executable
  baseline before proposing a modification. Paper2Agent is an upstream
  example of turning paper methods into usable tools.
  [Paper2Agent](https://github.com/jmiao24/Paper2Agent)
- Treat the scoring or training rule as an intervention. Snorkel's binary-gated
  GRPO experiment suggests a reusable design for rare successes: compare
  algorithms under comparable data and rollout budgets, with separate held-out
  tasks. Its single training run per method also makes replication across seeds
  a useful follow-up. [Snorkel GDPval study](https://snorkel.ai/blog/gdpval-agents-rare-success/)
- Study concision as an efficiency intervention. Record accuracy, output
  tokens and latency, and set the required accuracy level before selecting
  a candidate. [Concise Reasoning](https://github.com/ai-wand/concise-reasoning)

Record the closest prior work, proposed mechanism and result that would
falsify it. A candidate earns a narrower novelty claim when the evidence
survives held-out tests, ablations and independent reproduction.
