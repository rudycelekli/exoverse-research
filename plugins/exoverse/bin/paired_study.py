"""Paired offline studies and deterministic, evidence-pinned research drafts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path

import answer_study
import monitor_study
import observed_study
from starter_study import MEANS, TRIALS, canonical, feedback, measure

SCHEMA = "exoverse.plugin-paired-study.v1"
SEEDS = (17, 29, 41, 53, 67)
DIRECTIONS = ("lower", "higher", "unchanged")
METRIC = "expected_reward_lost_hundredths"
LIMIT = 32768

RUN_TOOL = "exoverse_run_local_comparison"
OBSERVED_TOOL = "exoverse_analyze_paired_outcomes"
VERIFY_TOOL = "exoverse_verify_local_comparison"
MONITOR_TOOL = "exoverse_run_monitor_comparison"


def protocol(question: str, baseline: int | str, treatment: int | str, prediction: str,
             template: str = "exploration") -> dict:
    if (not isinstance(question, str) or not question.strip() or len(question) > 400
            or not question.isprintable()):
        raise ValueError("Supply a single printable question of at most 400 characters.")
    if template == "exploration":
        if any(type(value) is not int or not 0 <= value <= 800 for value in (baseline, treatment)):
            raise ValueError("Exploration values must be integers from 0 through 800.")
    elif template == "monitor":
        if baseline not in monitor_study.SIGNALS or treatment not in monitor_study.SIGNALS:
            raise ValueError("Choose activity or ledger for each monitor arm.")
    else:
        raise ValueError("Unknown paired study template.")
    if baseline == treatment:
        raise ValueError("Choose different values for the two arms.")
    if prediction not in DIRECTIONS:
        raise ValueError("Predict lower, higher, or unchanged for the template's outcome.")
    spec = {"question": question.strip(), "baseline": baseline, "treatment": treatment, "prediction": prediction}
    return {**spec, "template": template} if template == "monitor" else spec


def compare(spec: dict) -> dict:
    if spec.get("template") in ("observed", "answer_key"):
        evaluator = answer_study if spec["template"] == "answer_key" else observed_study
        receipt = evaluator.compare(**{key: value for key, value in spec.items() if key != "template"})
        return {**receipt, "protocol_sha256": digest(canonical(receipt["protocol"]))}
    spec = protocol(**spec)
    if spec.get("template") == "monitor":
        return {**monitor_study.compare(spec), "protocol_sha256": digest(canonical(spec))}
    pairs = []
    for seed in SEEDS:
        streams = feedback(seed)
        baseline = measure(True, streams, exploration=spec["baseline"])
        treatment = measure(True, streams, exploration=spec["treatment"])
        pairs.append({
            "seed": seed, "baseline": baseline, "treatment": treatment,
            "delta": treatment[METRIC] - baseline[METRIC],
        })
    delta = sum(row["delta"] for row in pairs)
    direction = "lower" if delta < 0 else "higher" if delta > 0 else "unchanged"
    return {
        "schema": SCHEMA, "protocol": spec, "protocol_sha256": digest(canonical(spec)),
        "simulation": {
            "setting": "three seeded Bernoulli choices", "reward_probabilities_percent": list(MEANS),
            "trials_per_arm_per_seed": TRIALS, "seeds": list(SEEDS),
            "changed_variable": "exploration_weight_hundredths", "metric": METRIC,
        },
        "pairs": pairs, "delta_total_hundredths": delta, "direction": direction,
        "prediction_matched": direction == spec["prediction"], "model_calls": 0,
    }


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def paper(receipt: dict, seal: str) -> str:
    if receipt["schema"] == answer_study.SCHEMA:
        return answer_study.paper(receipt, seal)
    if receipt["schema"] == observed_study.SCHEMA:
        return observed_study.paper(receipt, seal)
    if receipt["schema"] == monitor_study.SCHEMA:
        return monitor_study.paper(receipt, seal)
    spec, pairs = receipt["protocol"], receipt["pairs"]
    rows = "\n".join(
        f"| {row['seed']} | {row['baseline'][METRIC] / 100:.2f} | "
        f"{row['treatment'][METRIC] / 100:.2f} | {row['delta'] / 100:+.2f} |" for row in pairs
    )
    mean = receipt["delta_total_hundredths"] / len(pairs) / 100
    match = "matched" if receipt["prediction_matched"] else "did not match"
    return f"""# Paired simulation study

## Research question

    {spec['question']}

## Prediction

We predicted {spec['prediction']} expected reward loss in the treatment arm.

## Method

We changed the exploration weight from {spec['baseline'] / 100:.2f} to {spec['treatment'] / 100:.2f}
in a UCB-style policy. Both arms ran {TRIALS} trials per seed with the same three reward
probabilities and the same seeded reward stream for each choice. The outcome is expected reward
lost relative to always picking the best choice. Lower values are better.

## Results

| Seed | Baseline loss | Treatment loss | Treatment minus baseline |
| --- | ---: | ---: | ---: |
{rows}

The treatment had **{receipt['direction']}** expected reward loss, with a mean paired difference
of **{mean:+.2f}**. The result {match} the recorded prediction.

## Scope

This is a descriptive result from {len(pairs)} simulated pairs. It does not establish a
population effect or a result in a different environment. No model was called.

## Reproduce

The accompanying `study.json` contains the protocol, matched outcomes and evidence.
Retain the original digest independently. Replay the export using
`exoverse-plugin paired verify PATH --sha256 {seal}`.
The verifier recomputes both the receipt and this draft.

- Evidence SHA-256: `{seal}`
- Protocol SHA-256: `{receipt['protocol_sha256']}`
- Method reference: [Auer et al., Finite-time Analysis of the Multiarmed Bandit Problem](https://doi.org/10.1023/A:1013689704352)
"""


def replay_receipt(raw: bytes, seal: str) -> dict:
    if len(raw) > LIMIT or digest(raw) != seal:
        raise ValueError("The bundle does not match the retained evidence digest or exceeds the size limit.")
    try:
        receipt = json.loads(raw)
        if not isinstance(receipt, dict) or receipt.get("schema") not in (SCHEMA, monitor_study.SCHEMA, observed_study.SCHEMA, answer_study.SCHEMA):
            raise ValueError("Choose a paired study receipt.")
        replay = compare(receipt["protocol"])
    except (AttributeError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError("The paired study protocol is invalid.") from error
    if canonical(replay) != raw:
        raise ValueError("The paired results did not reproduce.")
    draft = paper(replay, seal)
    return {"verified": True, "sha256": seal, "paper_sha256": digest(draft.encode()),
            "pairs": len(replay["pairs"]), "model_calls": 0, "receipt": replay, "paper": draft}


def replay_bundle(raw: bytes, draft: str, seal: str) -> dict:
    if len(draft.encode()) > LIMIT:
        raise ValueError("The bundle does not match the retained evidence digest or exceeds the size limit.")
    result = replay_receipt(raw, seal)
    if result["paper"] != draft:
        raise ValueError("The paper draft did not reproduce.")
    return result


def verify(raw: bytes, draft: str, seal: str) -> dict:
    result = replay_bundle(raw, draft, seal)
    del result["receipt"], result["paper"]
    return result


def run(spec: dict) -> dict:
    receipt = compare(spec)
    raw = canonical(receipt)
    seal = digest(raw)
    draft = paper(receipt, seal)
    return {**verify(raw, draft, seal), "receipt": receipt, "paper": draft}


def read_file(path: Path, limit: int = LIMIT) -> bytes:
    if not path.is_file():
        raise ValueError("The bundle is missing a required regular file.")
    with path.open("rb") as handle:
        return handle.read(limit + 1)


def read_json_file(path: Path):
    raw = read_file(path)
    if len(raw) > LIMIT:
        raise ValueError("The input JSON exceeds the size limit.")
    try:
        return json.loads(raw)
    except RecursionError as error:
        raise ValueError("The input JSON is too deeply nested.") from error


def write_bundle(out: Path, report: dict) -> None:
    files = {
        "paper.md": report.pop("paper").encode(),
        "study.json": canonical(report.pop("receipt")),
    }
    out.mkdir()
    with ExitStack() as cleanup:
        cleanup.callback(out.rmdir)
        for name, content in files.items():
            path = out / name
            with path.open("xb") as handle:
                cleanup.callback(path.unlink)
                handle.write(content)
        cleanup.pop_all()
    report["directory"] = str(out)


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exoverse-plugin paired")
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("run")
    start.add_argument("--question", required=True)
    start.add_argument("--template", choices=("exploration", "monitor"), default="exploration")
    start.add_argument("--baseline", required=True, help="exploration weight in hundredths, or monitor signal")
    start.add_argument("--treatment", required=True, help="exploration weight in hundredths, or monitor signal")
    start.add_argument("--prediction", choices=DIRECTIONS, required=True)
    start.add_argument("--out", type=Path, required=True, help="new directory for study.json and paper.md")
    observed = sub.add_parser("analyze", help="compare matched scores from a local CSV")
    observed.add_argument("csv", type=Path)
    observed.add_argument("--question", required=True)
    observed.add_argument("--metric", required=True, help="metric name and units")
    observed.add_argument("--baseline-label", required=True)
    observed.add_argument("--treatment-label", required=True)
    observed.add_argument("--out", type=Path, required=True, help="new directory for study.json and paper.md")
    key = sub.add_parser("key", help="fingerprint a JSON list of reference answers")
    key.add_argument("references", type=Path)
    key.add_argument("--out", required=True, type=Path, help="new answer-key JSON file")
    score = sub.add_parser("score", help="score matched responses using a retained answer key")
    score.add_argument("responses", type=Path, help="JSON list of paired answers")
    score.add_argument("--key", required=True, type=Path)
    score.add_argument("--key-sha256", required=True)
    for field in answer_study.METADATA_FIELDS:
        score.add_argument("--" + field.replace("_", "-"), required=True)
    score.add_argument("--out", required=True, type=Path)
    check = sub.add_parser("verify")
    check.add_argument("directory", type=Path)
    check.add_argument("--sha256", required=True)
    reproduce = sub.add_parser("reproduce", help="verify evidence and regenerate the receipt and paper")
    reproduce.add_argument("source", type=Path, help="bundle directory or study.json")
    reproduce.add_argument("--sha256", required=True, help="original study fingerprint")
    reproduce.add_argument("--out", type=Path, required=True, help="new directory for the regenerated bundle")
    args = parser.parse_args(argv)
    try:
        if args.action == "run":
            convert = int if args.template == "exploration" else str
            spec = protocol(args.question, convert(args.baseline), convert(args.treatment),
                            args.prediction, args.template)
            report = run(spec)
            write_bundle(args.out, report)
        elif args.action == "analyze":
            raw = read_file(args.csv)
            if len(raw) > LIMIT:
                raise ValueError("The scores CSV exceeds the size limit.")
            report = run({
                "template": "observed", "question": args.question, "metric": args.metric,
                "baseline_label": args.baseline_label, "treatment_label": args.treatment_label,
                "rows": observed_study.read_csv(raw),
            })
            write_bundle(args.out, report)
        elif args.action == "key":
            report = answer_study.create_key(read_json_file(args.references))
            with tempfile.NamedTemporaryFile(dir=args.out.parent) as temporary:
                temporary.write(canonical(report.pop("key")))
                temporary.flush()
                os.link(temporary.name, args.out)
            report["file"] = str(args.out)
        elif args.action == "score":
            spec = {field: getattr(args, field) for field in answer_study.METADATA_FIELDS}
            spec.update(key=read_json_file(args.key), key_sha256=args.key_sha256,
                        responses=read_json_file(args.responses))
            report = run(answer_study.from_answers(spec))
            write_bundle(args.out, report)
        elif args.action == "reproduce":
            has_paper = args.source.is_dir()
            if has_paper:
                report = replay_bundle(read_file(args.source / "study.json"),
                                       read_file(args.source / "paper.md").decode(), args.sha256)
            else:
                report = replay_receipt(read_file(args.source), args.sha256)
            write_bundle(args.out, report)
            report["source_paper_verified"] = has_paper
        else:
            report = verify(read_file(args.directory / "study.json"),
                            read_file(args.directory / "paper.md").decode(), args.sha256)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


TOOLS = (
    {"name": RUN_TOOL, "description": "Run two paired offline simulation arms that differ only in exploration weight. "
                                     "Returns a verified receipt and a Markdown paper draft.",
     "inputSchema": {"type": "object", "additionalProperties": False,
                     "required": ["question", "baseline", "treatment", "prediction"], "properties": {
                         "question": {"type": "string", "maxLength": 400},
                         "baseline": {"type": "integer", "minimum": 0, "maximum": 800},
                         "treatment": {"type": "integer", "minimum": 0, "maximum": 800},
                         "prediction": {"enum": list(DIRECTIONS)},
                     }}},
    {"name": MONITOR_TOOL, "description": "Compare activity and ledger alerts on paired simulated completion reports.",
     "inputSchema": {"type": "object", "additionalProperties": False,
                     "required": ["question", "baseline", "treatment", "prediction"], "properties": {
                         "question": {"type": "string", "maxLength": 400},
                         "baseline": {"enum": list(monitor_study.SIGNALS)},
                         "treatment": {"enum": list(monitor_study.SIGNALS)},
                         "prediction": {"enum": list(DIRECTIONS)},
                     }}},
    {"name": OBSERVED_TOOL, "description": "Analyze researcher-supplied matched scores and return a receipt and draft.",
     "inputSchema": {"type": "object", "additionalProperties": False,
                     "required": sorted(observed_study.FIELDS), "properties": {
                         **{key: {"type": "string", "maxLength": limit}
                            for key, limit in observed_study.TEXT_LIMITS.items()},
                         "rows": {"type": "array", "minItems": 1, "maxItems": observed_study.MAX_PAIRS,
                                  "items": {"type": "object", "additionalProperties": False,
                                            "required": list(observed_study.COLUMNS), "properties": {
                                                "case_id": {"type": "string", "maxLength": 64},
                                                **{key: {"type": "integer", "minimum": -observed_study.MAX_SCORE,
                                                         "maximum": observed_study.MAX_SCORE}
                                                   for key in observed_study.COLUMNS[1:]},
                                            }}},
                     }}},
    *answer_study.TOOLS,
    {"name": VERIFY_TOOL, "description": "Independently replay a paired study receipt and its exact paper draft.",
     "inputSchema": {"type": "object", "additionalProperties": False,
                     "required": ["receipt", "paper", "sha256"], "properties": {
                         "receipt": {"type": "object"}, "paper": {"type": "string"}, "sha256": {"type": "string"},
                     }}},
)


def tool_call(name: str, arguments: dict) -> dict:
    if name in (RUN_TOOL, MONITOR_TOOL) and arguments.keys() == {"question", "baseline", "treatment", "prediction"}:
        return run({**arguments, "template": "monitor"} if name == MONITOR_TOOL else arguments)
    if name == OBSERVED_TOOL and arguments.keys() == observed_study.FIELDS:
        return run({**arguments, "template": "observed"})
    if name == answer_study.KEY_TOOL and arguments.keys() == {"references"}:
        return answer_study.create_key(arguments["references"])
    if name == answer_study.SCORE_TOOL and arguments.keys() == answer_study.SCORE_FIELDS:
        return run(answer_study.from_answers(arguments))
    if name == VERIFY_TOOL and arguments.keys() == {"receipt", "paper", "sha256"}:
        if (isinstance(arguments["receipt"], dict) and isinstance(arguments["paper"], str)
                and isinstance(arguments["sha256"], str)):
            return verify(canonical(arguments["receipt"]), arguments["paper"], arguments["sha256"])
    raise ValueError("Supply the exact fields listed in the tool schema.")
