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

Ask your agent: **“Run my first Exoverse study without a prediction.”**
The offline starter compares two strategies and can verify the receipt through
MCP. To bring your own question about exploration, ask for a paired comparison
and a short evidence-backed paper. Share both files and retain the original
digest separately.

For a direct CLI from the extracted package, run the study and set `study_sha` to the fingerprint printed by the paired run before invoking verify.

```sh
plugins/exoverse/bin/exoverse-plugin starter run --out first-study.json
plugins/exoverse/bin/exoverse-plugin paired run \
  --question 'Does reducing exploration lower expected reward loss?' \
  --baseline 200 --treatment 50 --prediction lower --out study
plugins/exoverse/bin/exoverse-plugin paired verify study --sha256 "${study_sha:?Set study_sha from the paired run}"
```

## Compare results from your own experiment

Run the same cases under two settings and record a score for each. Save
this example as `scores.csv`:

```csv
case_id,baseline,treatment
question-01,3,4
question-02,4,3
question-03,2,4
```

```sh
plugins/exoverse/bin/exoverse-plugin paired analyze scores.csv \
  --question 'Did adding an example change benchmark scores?' \
  --metric 'rubric points out of 5' \
  --baseline-label 'Original prompt' --treatment-label 'Prompt with one example' \
  --out my-study
```

Use one metric for both settings, one row per case, and up to 50 unique
case IDs. Use integer scores and name the units, such as milliseconds or
hundredths of a point. The bundle contains the supplied scores.

The draft reports the per-case differences and how often scores went up,
down, or stayed the same. A reviewer can replay the analysis using the
fingerprint. Verification covers the arithmetic on the supplied scores.

## Score two sets of answers against a reference key

Save reference answers as a JSON list, for example:

```json
[{"case_id": "day-01", "expected": "Saturday"}]
```

Create the fingerprint before collecting answers and keep the reported
`sha256` separately:

```sh
plugins/exoverse/bin/exoverse-plugin paired key references.json --out key.json
```

Run the same cases under both settings, then put the answers in
`responses.json`, with the same IDs:

```json
[{"case_id": "day-01", "baseline": "Friday", "treatment": "Saturday"}]
```

Replace `ORIGINAL_KEY_FINGERPRINT` with the saved value:

```sh
plugins/exoverse/bin/exoverse-plugin paired score responses.json \
  --key key.json --key-sha256 ORIGINAL_KEY_FINGERPRINT \
  --question 'Did one example improve exact answers?' \
  --baseline-label 'Original prompt' --treatment-label 'Prompt with one example' \
  --out scored-study
```

The scorer trims surrounding whitespace, normalizes Unicode, and then
matches case-sensitively. Use single-line references of up to 128 UTF-8 bytes and responses up to 1024 bytes.
The output contains answer hashes and binary scores. Hashes of short or
predictable answers may be guessable. Replay checks the scoring and
arithmetic. Retain separate evidence of when the key was frozen and how
the answers were obtained.

## Collect both sets of answers from a local model

With an existing [Ollama](https://docs.ollama.com/) install and a local
GGUF model already on disk, save up to 12 cases in `cases.json`:

```json
[{"case_id": "day-01", "prompt": "Which day comes after Friday?"}]
```

If you plan to score the answers, save the reference with `paired key`
before running either setting. Then run this, substituting your installed
model tag if needed:

```sh
plugins/exoverse/bin/exoverse-plugin collect cases.json \
  --model qwen2.5:7b \
  --baseline-system 'Answer in one sentence.' \
  --treatment-system 'Answer with only the requested word.' \
  --out collected
```

The command sends each case twice to Ollama on `127.0.0.1`, keeps decoding
settings fixed, and alternates which setting goes first. It checks the
installed model fingerprint before and after the run. A complete run saves
`collected/responses.json` for `paired score` and `collected/collection.json`
with the prompts, settings, model fingerprint and execution order.
These files contain raw study inputs or answers. Keep them local unless
you intend to share that content. Use a trusted local Ollama service.
Exoverse connects directly to loopback and does not install any model.
Reproducing the scored study replays scoring from the recorded answers.

## Run and verify a complete local experiment

Create the reference key with `paired key` and save the printed fingerprint
before running either setting. With the same `cases.json` as above, run
collection and scoring together:

```sh
plugins/exoverse/bin/exoverse-plugin experiment run cases.json \
  --model qwen2.5:7b --key key.json --key-sha256 ORIGINAL_KEY_FINGERPRINT \
  --baseline-system 'Answer in one sentence.' \
  --treatment-system 'Answer with only the requested word.' \
  --question 'Does a short answer prompt improve exact-match accuracy?' \
  --baseline-label 'One sentence' --treatment-label 'One word' \
  --out experiment
```

Keep the printed `experiment_sha256` separately. A reviewer needs the
experiment folder and that fingerprint:

```sh
plugins/exoverse/bin/exoverse-plugin experiment verify experiment \
  --sha256 ORIGINAL_EXPERIMENT_FINGERPRINT
```

Verification checks the exported files and recomputes the scores and paper
from the collected answers without calling a model. The experiment folder
includes raw prompts and responses. Share it only when those inputs and
outputs are appropriate to disclose. The scored study and paper can be
shared independently for scoring replay.

## Reproduce a shared study

Ask the sender for the original SHA-256 fingerprint separately from the files.
Use the bundle folder as the source to check both files and regenerate them:

```sh
plugins/exoverse/bin/exoverse-plugin paired reproduce shared-study \
  --sha256 ORIGINAL_FINGERPRINT --out reproduced-study
```

If you only received `study.json`, pass that file as the source. Exoverse
regenerates the paper from the validated simulation and reports
`source_paper_verified: false` because there was no supplied draft to check.
The output directory must be new.

## Audit alerts about incorrect completion reports

Run a second template with honest and incorrect reports from the same
simulated completion ledger. The only change is which signal the monitor
uses. Compare missed reports as well as false alarms.

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

## Package identity and license

This standalone package is licensed under Apache-2.0. See [LICENSE](../LICENSE)
and [NOTICE](../NOTICE). The release scope is the files in this archive.
`PACKAGE-MANIFEST.json` identifies the exact source revision and includes the
size and SHA-256 for every packaged file other than the manifest itself.
