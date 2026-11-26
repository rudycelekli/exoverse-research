# More ways to use Exoverse

Download and extract the [0.6.6 release ZIP](https://github.com/rudycelekli/exoverse-research/releases/tag/v0.6.6). Run these commands from the extracted folder. `sha256` is the 64-character fingerprint printed by a study run. Save it separately from the files.

## Audit alerts about incorrect completion reports

Run a second template with honest and incorrect reports from the same
simulated completion ledger. The only change is which signal the monitor
uses. Compare missed reports as well as false alarms. Set `monitor_sha` to the fingerprint printed by the run before invoking verify.

```sh
plugins/exoverse/bin/exoverse-plugin paired run --template monitor \
  --question 'Will the ledger signal reduce false alarms?' \
  --baseline activity --treatment ledger --prediction lower --out monitor-study
plugins/exoverse/bin/exoverse-plugin paired verify monitor-study --sha256 "${monitor_sha:?Set monitor_sha from the monitor run}"
```

## Get an independent local review

First run the monitor study above and retain its digest. Replay it without
any adapters:

```sh
plugins/exoverse/bin/exoverse-plugin review monitor-study \
  --sha256 "${monitor_sha:?Set monitor_sha from the monitor run}" --out local-review
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
  --sha256 "${monitor_sha:?Set monitor_sha from the monitor run}" --out adapter-review \
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
