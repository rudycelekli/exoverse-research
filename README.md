# Exoverse Research

Make a prediction, run both sides of an experiment, and hand someone a result
they can verify. Exoverse runs its bundled experiments locally with Python 3.9
or newer. The research tools require no runtime wheel, GPU, model key or
hosted account.

## Install from this extracted package

In a supported host, point its local marketplace command at this package root:

```sh
claude plugin marketplace add /path/to/extracted-package
claude plugin install exoverse@exoverse-research

codex plugin marketplace add /path/to/extracted-package
codex plugin add exoverse@exoverse-research
```

Ask your agent: **“Help me make a prediction and run my first Exoverse study.”**
The offline starter compares two strategies and can verify the receipt through
MCP. To bring your own question about exploration, ask for a paired comparison
and a short evidence-backed paper. Share both files and retain the original
digest separately.

For a direct CLI from the extracted package:

```sh
plugins/exoverse/bin/exoverse-plugin starter run --prediction adaptive --out first-study.json
plugins/exoverse/bin/exoverse-plugin paired run \
  --question 'Does reducing exploration lower expected reward loss?' \
  --baseline 200 --treatment 50 --prediction lower --out study
plugins/exoverse/bin/exoverse-plugin paired verify study --sha256 <printed-digest>
```

## Audit alerts about incorrect completion reports

Run a second template with honest and incorrect reports from the same
simulated completion ledger. The only change is which signal the monitor
uses. Compare missed reports as well as false alarms.

```sh
plugins/exoverse/bin/exoverse-plugin paired run --template monitor \
  --question 'Will the ledger signal reduce false alarms?' \
  --baseline activity --treatment ledger --prediction lower --out monitor-study
plugins/exoverse/bin/exoverse-plugin paired verify monitor-study --sha256 <printed-digest>
```

## Get an independent local review

First run the monitor study above and retain its digest. Replay it without
any adapters:

```sh
plugins/exoverse/bin/exoverse-plugin review monitor-study \
  --sha256 <retained-digest> --out local-review
```

For the optional external policy evaluator and local task tracking, set up
separate local installs using Python 3.10+ and Node. The archive installs
neither adapter.

```sh
python3.12 -m venv .ifixai-review
.ifixai-review/bin/python -m pip install ifixai==4.3.0
mkdir review-tools
npm --prefix review-tools install --ignore-scripts ruflo@3.80.0 @claude-flow/cli@3.80.0
plugins/exoverse/bin/exoverse-plugin review monitor-study \
  --sha256 <retained-digest> --out adapter-review \
  --ifixai-python "$PWD/.ifixai-review/bin/python" \
  --ruflo "$PWD/review-tools/node_modules/.bin/ruflo"
```

iFixAI passively checks recorded decisions against the declared classification
policy. Ruflo records local task completion with the evidence and review
digests. The adapter calls use synthetic case labels and decisions. No
research question or draft is sent to either adapter. The reports are
evidence about two fixed monitor rules and their labels.

## Work with a research team

The bundled workbench skill helps separate questions, measurements, known
limits and conclusions. The team skill gives a host that already supports
delegation a coordinator, experiment runner and independent reviewer
workflow. A host without delegation can still run and verify the study.
Keep local project notes indexed by receipt digest. Reuse the same workflow
for development questions, such as testing a single application change
against a baseline.

Ruflo and iFixAI have optional local review adapters. RuVector, Claude-mem
and Firecrawl can be connected separately in an authorized workspace.
This profile provides the local study, verification and research skills
without installing any third-party runtime.

## Package identity and license

This standalone package is licensed under Apache-2.0. See [LICENSE](LICENSE)
and [NOTICE](NOTICE). The release scope is the files in this archive.
`PACKAGE-MANIFEST.json` identifies the exact source revision and includes the
size and SHA-256 for every packaged file other than the manifest itself.
