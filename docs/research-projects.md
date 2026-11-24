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
