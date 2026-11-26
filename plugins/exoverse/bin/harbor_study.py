"""Verify imported Harbor trials against a frozen agent comparison."""

import argparse
import json
from pathlib import Path

from research_spec import branch, decode, load, load_frozen
from workflow_study import LIMIT, canonical, digest, mapping, name, read

SCHEMA = "exoverse.harbor-study.v1"
TRIAL_BOOKKEEPING = {"job_id", "trial_name", "trials_dir"}


def _number(value):
    if type(value) not in (float, int):
        raise ValueError("Harbor rewards and rubric thresholds must be numbers.")
    return value


def compare(baseline, candidate, trials, parent_sha):
    expected = branch(baseline, parent_sha, "agent", candidate["protocol"]["variables"]["agent"])
    if canonical(expected) != canonical(candidate):
        raise ValueError("Expected a verified branch changing only the Harbor agent.")
    plan = baseline["protocol"]
    env = mapping(plan["environment"], {"adapter", "task_name", "task_checksum"}, "Harbor environment")
    if env["adapter"] != "harbor":
        raise ValueError("The frozen environment must use Harbor.")
    if plan["seeds"] != [0]:
        raise ValueError("This importer supports one trial per arm with seed placeholder 0.")
    rubric = mapping(plan["rubric"], {"minimum_rewards"}, "Harbor rubric")
    thresholds = rubric["minimum_rewards"]
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("Provide at least one named minimum reward.")
    if not isinstance(trials, list) or len(trials) != 2:
        raise ValueError("Exactly two Harbor trial records are required.")
    if not env["task_checksum"] or trials[0]["id"] == trials[1]["id"]:
        raise ValueError("Pin the Harbor task checksum and provide two distinct trials.")
    baseline_config = trials[0]["config"]
    results = []
    for arm, spec, trial in zip(("baseline", "candidate"), (baseline, candidate), trials):
        agent = name(spec["protocol"]["variables"]["agent"])
        if (trial["task_name"] != env["task_name"] or trial["task_checksum"] != env["task_checksum"]
                or trial["agent_info"]["name"] != agent or trial["config"]["agent"]["name"] != agent):
            raise ValueError(f"{arm} trial differs from its frozen task or agent.")
        if trial["config"]["agent"] != {**trials[0]["config"]["agent"], "name": agent}:
            raise ValueError("Harbor agent settings besides the name differ between arms.")
        shared_fields = TRIAL_BOOKKEEPING | {"agent"}
        observed = {key: value for key, value in trial["config"].items() if key not in shared_fields}
        expected = {key: value for key, value in baseline_config.items() if key not in shared_fields}
        if canonical(observed) != canonical(expected):
            raise ValueError("Harbor trial settings besides the agent differ between arms.")
        if (not trial["finished_at"] or trial["exception_info"] is not None
                or any(step.get("exception_info") for step in trial.get("step_results") or [])):
            raise ValueError(f"{arm} trial did not finish successfully.")
        rewards = trial["verifier_result"]["rewards"]
        scores = {key: {"reward": _number(rewards[key]), "minimum": _number(minimum),
                        "passed": rewards[key] >= minimum} for key, minimum in thresholds.items()}
        results.append({"arm": arm, "agent": agent, "trial_id": trial["id"], "rubric": scores,
                        "passed": all(score["passed"] for score in scores.values())})
    return {"schema": SCHEMA, "baseline": baseline, "candidate": candidate, "trials": trials,
            "results": results, "judge_status": "pending" if plan["judge"] is not None else "unconfigured"}


def cli(argv):
    parser = argparse.ArgumentParser(prog="exoverse-plugin harbor")
    commands = parser.add_subparsers(dest="mode", required=True)
    ingest = commands.add_parser("import")
    for field in ("baseline", "candidate", "baseline_trial", "candidate_trial"):
        ingest.add_argument(field, type=Path)
    ingest.add_argument("--parent-sha256", required=True)
    ingest.add_argument("--candidate-sha256", required=True)
    ingest.add_argument("--out", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("evidence", type=Path)
    verify.add_argument("--sha256", required=True)
    verify.add_argument("--draft", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "import":
            candidate = read(args.candidate)
            if digest(candidate) != args.candidate_sha256:
                raise ValueError("Candidate fingerprint differs.")
            child = decode(candidate)
            if canonical(child) != candidate:
                raise ValueError("Candidate protocol bytes are not canonical.")
            report = compare(load_frozen(args.baseline), child,
                             [load(args.baseline_trial), load(args.candidate_trial)], args.parent_sha256)
            raw = canonical(report)
            if len(raw) > LIMIT:
                raise ValueError("Harbor study evidence exceeds 64 KiB.")
            with args.out.open("xb") as output:
                output.write(raw)
        else:
            raw = read(args.evidence)
            if digest(raw) != args.sha256:
                raise ValueError("Evidence fingerprint differs.")
            supplied = decode(raw)
            baseline = supplied["baseline"]
            report = compare(baseline, supplied["candidate"], supplied["trials"], digest(canonical(baseline)))
            if canonical(report) != raw:
                raise ValueError("Harbor results did not reproduce.")
            if args.draft:
                question = report["baseline"]["protocol"]["question"]
                with args.draft.open("x", encoding="utf-8") as draft:
                    draft.write(f"# Harbor study draft\n\n{question}\n\n"
                                f"Evidence SHA-256: `{digest(raw)}`\n\n## Results\n\n"
                                f"```json\n{json.dumps(report['results'], indent=2)}\n```\n\n"
                                "## Limitations\n\nScores were recomputed from two imported Harbor trial records. "
                                "This verifies the exported records and rubric arithmetic. "
                                f"AI judge status: {report['judge_status']}.\n")
        print(json.dumps({"sha256": digest(raw), "verified": args.mode == "verify",
                          "judge_status": report["judge_status"], "results": report["results"]}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
