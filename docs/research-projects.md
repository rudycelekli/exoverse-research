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

Run from the extracted package root. After each freeze or branch command,
set `baseline_sha` or `candidate_sha` to its printed SHA-256 before
running the command that uses it.

```sh
python3 plugins/exoverse/bin/exoverse-plugin spec freeze protocol.json --out baseline.json
python3 plugins/exoverse/bin/exoverse-plugin spec branch baseline.json prompt new-prompt.json \
  --parent-sha256 "$baseline_sha" --out candidate.json
python3 plugins/exoverse/bin/exoverse-plugin spec verify baseline.json candidate.json \
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

## Import a Harbor agent comparison

Freeze `environment` with `adapter: "harbor"`, `task_name` and
`task_checksum` as reported by Harbor. Declare `variables.agent` and branch
that variable to the candidate agent. Use `seeds: [0]` for this one-trial,
unseeded importer. Define `rubric.minimum_rewards` as a mapping from Harbor
verifier metric names to passing thresholds. Arrange for the task verifier to
emit those metrics.

Run each arm in Harbor using the same task and environment settings. Feed the
per-trial results into Exoverse after both finish. Set `evidence_sha` to
the SHA-256 printed by import before running verify.

```sh
python3 plugins/exoverse/bin/exoverse-plugin harbor import baseline.json candidate.json baseline/result.json candidate/result.json \
  --parent-sha256 "$baseline_sha" --candidate-sha256 "$candidate_sha" --out harbor-evidence.json
python3 plugins/exoverse/bin/exoverse-plugin harbor verify harbor-evidence.json --sha256 "$evidence_sha" --draft paper.md
```

The verifier needs the bundle and its separately retained fingerprint.
Drafts replay deterministic scores and display judge status. Review trial
configuration and paths before sharing a bundle. A judge configuration in
the spec records research intent, and live judge evaluation is pending.

### Frozen retrieval fallback example

The example under `examples/harbor/retrieval` uses a synthetic corpus, three
answerable questions, two missing-evidence questions and exact source-span labels.
The policies share initial retrieval and differ only in their fallback action.
Use Harbor 0.25.0 and Docker. Run the script with the Python interpreter in the
environment where Harbor is installed. The output directory must be new.

```sh
python examples/harbor/run_retrieval_study.py ./retrieval-run
```

The runner freezes both specs, runs independent Docker trials, recomputes
citation support and abstention from the retained raw answers, and exports
`paper.md`. Keep `verification.json`, the job folders and frozen evidence with
the draft. A second reader can use `harbor verify` on `evidence.json` as above
and replay each raw answer score with standard Python:

```sh
python examples/harbor/retrieval/tests/score.py path/to/verifier/answers.json \
  examples/harbor/retrieval/tests/labels.json examples/harbor/retrieval/environment/corpus.json
```

To check the complete retained run, use the same reviewed source revision and
retain the SHA-256 of both `evidence.json` and `verification.json` when you
first receive them. Pass those fingerprints to the offline verifier:

```sh
python3 examples/harbor/run_retrieval_study.py ./retrieval-run --verify \
  --evidence-sha256 "$evidence_sha" --receipt-sha256 "$receipt_sha"
```

The command checks both Harbor records, raw answers, recomputed scores and the
paper. It runs with standard Python and needs no model key, Docker or Harbor.

New runs retain the task files in `retrieval/` inside the output directory.
Keep that directory with the other artifacts. The offline verifier checks the
recorded inputs before rescoring. It reports `inputs_verified: false` for
older receipts without input fingerprints.

Current runs also freeze the canonical input manifest fingerprint inside the
baseline protocol before launching Harbor. The candidate inherits that
fingerprint. The offline verifier reports `inputs_frozen: true` only when the
receipt's input manifest matches the frozen protocol. Earlier runs retain
their existing verification behavior and report `inputs_frozen: false`.

The offline verifier also returns a `questions` array. Each entry shows the
expected source span or abstention, both submissions and the outcome for each
arm. Use it to review the individual cases behind the aggregate score.
