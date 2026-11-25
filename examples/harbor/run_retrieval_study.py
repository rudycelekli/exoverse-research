"""Run the frozen retrieval comparison using Python from the Harbor environment."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().with_name("retrieval")
PLUGIN = ROOT / "plugins/exoverse/bin/exoverse-plugin"


def cli(*args):
    result = subprocess.check_output([sys.executable, str(PLUGIN), *map(str, args)])
    return json.loads(result)


def load(path):
    return json.loads(path.read_bytes())


def main(output):
    from harbor.models.task.task import Task

    output.mkdir(mode=0o700)
    protocol_path = output / "protocol.json"
    protocol_path.write_text(json.dumps({
        "question": "Does grounded fallback improve citation support and abstention?",
        "hypothesis": "Grounded fallback improves both scores on this frozen synthetic corpus.",
        "environment": {"adapter": "harbor", "task_name": TASK.name, "task_checksum": Task(TASK).checksum},
        "rubric": {"minimum_rewards": {"citation_support": 1, "abstention": 1}},
        "judge": None,
        "seeds": [0],
        "budget_microusd": 0,
        "stopping_rule": "One completed deterministic trial per policy.",
        "variables": {"agent": {"name": "direct", "import_path": "policies:Direct"}},
    }))
    replacement = output / "replacement.json"
    replacement.write_text(json.dumps({"name": "grounded", "import_path": "policies:Grounded"}))
    baseline, candidate = output / "baseline.json", output / "candidate.json"
    parent = cli("spec", "freeze", protocol_path, "--out", baseline)["sha256"]
    child = cli("spec", "branch", baseline, "agent", replacement, "--parent-sha256", parent,
                "--out", candidate)["sha256"]
    env = {key: os.environ[key] for key in ("PATH", "HOME", "USER", "TMPDIR", "DOCKER_HOST")
           if key in os.environ}
    env.update(PYTHONPATH=str(TASK), PYTHONDONTWRITEBYTECODE="1")
    trials = []
    for arm in ("Direct", "Grounded"):
        subprocess.run(["harbor", "run", "-p", str(TASK), "-a", f"policies:{arm}",
                        "--jobs-dir", str(output / "jobs"), "--job-name", arm], check=True, env=env)
        trial, = (output / "jobs" / arm).glob("*/result.json")
        trials.append(trial)
    evidence = output / "evidence.json"
    report = cli("harbor", "import", baseline, candidate, *trials, "--parent-sha256", parent,
                 "--candidate-sha256", child, "--out", evidence)
    checks = score_trials(trials)
    cli("harbor", "verify", evidence, "--sha256", report["sha256"], "--draft", output / "paper.md")
    (output / "verification.json").write_text(json.dumps({"evidence_sha256": report["sha256"],
                                                          "answer_checks": checks}, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def score_trials(trials):
    checks = {}
    for trial in trials:
        answers = trial.parent / "verifier/answers.json"
        score = json.loads(subprocess.check_output([
            sys.executable, str(TASK / "tests/score.py"), str(answers), str(TASK / "tests/labels.json"),
            str(TASK / "environment/corpus.json"),
        ]))
        recorded = load(trial)["verifier_result"]["rewards"]
        if score != recorded:
            raise ValueError("Offline answer scoring differs from Harbor.")
        checks[trial.parent.parent.name] = {
            "answers_sha256": hashlib.sha256(answers.read_bytes()).hexdigest(), "scores": score,
        }
    return checks


def verify(output, evidence_sha256, receipt_sha256):
    evidence = output / "evidence.json"
    receipt_bytes = (output / "verification.json").read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha256:
        raise ValueError("Verification receipt does not match its retained fingerprint.")
    receipt = json.loads(receipt_bytes)
    if receipt["evidence_sha256"] != evidence_sha256:
        raise ValueError("Receipt names a different evidence bundle.")

    with TemporaryDirectory() as folder:
        reproduced = Path(folder) / "paper.md"
        cli("harbor", "verify", evidence, "--sha256", evidence_sha256, "--draft", reproduced)
        if reproduced.read_bytes() != (output / "paper.md").read_bytes():
            raise ValueError("The retained paper differs from the replayed draft.")

    direct, = (output / "jobs/Direct").glob("*/result.json")
    grounded, = (output / "jobs/Grounded").glob("*/result.json")
    trials = [direct, grounded]
    if [load(trial) for trial in trials] != load(evidence)["trials"]:
        raise ValueError("The raw Harbor receipts differ from the embedded trial records.")
    if score_trials(trials) != receipt["answer_checks"]:
        raise ValueError("The raw answers differ from the verified scores or fingerprints.")
    return {"verified": True, "evidence_sha256": evidence_sha256, "answer_checks": receipt["answer_checks"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--evidence-sha256")
    parser.add_argument("--receipt-sha256")
    args = parser.parse_args()
    if args.verify != bool(args.evidence_sha256 and args.receipt_sha256):
        parser.error("Offline verification requires both retained SHA-256 fingerprints.")
    try:
        if args.verify:
            print(json.dumps(verify(args.output.resolve(), args.evidence_sha256, args.receipt_sha256), indent=2))
        else:
            main(args.output.resolve())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
