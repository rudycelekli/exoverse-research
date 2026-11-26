"""Run the frozen retrieval comparison using Python from the Harbor environment."""

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().with_name("retrieval")
PLUGIN = ROOT / "plugins/exoverse/bin/exoverse-plugin"

TASK_FILES = (
    "task.toml", "instruction.md", "policies.py", "environment/Dockerfile",
    "environment/corpus.json", "environment/questions.json", "environment/policy.py",
    "tests/labels.json", "tests/score.py", "tests/test.sh",
)


def input_hashes(task):
    return {name: hashlib.sha256((task / name).read_bytes()).hexdigest() for name in TASK_FILES}


def manifest_digest(inputs):
    raw = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def retain_task(output):
    snapshot = output / TASK.name
    for name in TASK_FILES:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TASK / name, target)
    return snapshot


def cli(*args):
    result = subprocess.check_output([sys.executable, str(PLUGIN), *map(str, args)])
    return json.loads(result)


def load(path):
    return json.loads(path.read_bytes())


def main(output):
    from harbor.models.task.task import Task

    output.mkdir(mode=0o700)
    task = retain_task(output)
    inputs = input_hashes(task)
    protocol_path = output / "protocol.json"
    protocol_path.write_text(json.dumps({
        "question": "Does grounded fallback improve citation support and abstention?",
        "hypothesis": "Grounded fallback improves both scores on this frozen synthetic corpus.",
        "environment": {
            "adapter": "harbor", "task_name": TASK.name, "task_checksum": Task(task).checksum,
            "input_manifest_sha256": manifest_digest(inputs),
        },
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
    env.update(PYTHONPATH=str(task), PYTHONDONTWRITEBYTECODE="1")
    trials = []
    for arm in ("Direct", "Grounded"):
        subprocess.run(["harbor", "run", "-p", str(task), "-a", f"policies:{arm}",
                        "--jobs-dir", str(output / "jobs"), "--job-name", arm], check=True, env=env)
        trial, = (output / "jobs" / arm).glob("*/result.json")
        trials.append(trial)
    evidence = output / "evidence.json"
    report = cli("harbor", "import", baseline, candidate, *trials, "--parent-sha256", parent,
                 "--candidate-sha256", child, "--out", evidence)
    if input_hashes(task) != inputs:
        raise ValueError("Study inputs changed after freezing.")
    checks = score_trials(trials, task)
    cli("harbor", "verify", evidence, "--sha256", report["sha256"], "--draft", output / "paper.md")
    (output / "verification.json").write_text(json.dumps({"evidence_sha256": report["sha256"],
                                                          "answer_checks": checks, "input_sha256": inputs}, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def score_trials(trials, task):
    checks = {}
    for trial in trials:
        answers = trial.parent / "verifier/answers.json"
        score = json.loads(subprocess.check_output([
            sys.executable, str(TASK / "tests/score.py"), str(answers), str(task / "tests/labels.json"),
            str(task / "environment/corpus.json"),
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
    bundle = load(evidence)
    if [load(trial) for trial in trials] != bundle["trials"]:
        raise ValueError("The raw Harbor receipts differ from the embedded trial records.")
    frozen_manifest = bundle["baseline"]["protocol"]["environment"].get("input_manifest_sha256")
    if frozen_manifest is not None:
        inputs = receipt.get("input_sha256")
        if not isinstance(inputs, dict) or manifest_digest(inputs) != frozen_manifest:
            raise ValueError("Receipt inputs do not match the frozen protocol.")
    task = TASK
    if "input_sha256" in receipt:
        task = output / TASK.name
        inputs = receipt["input_sha256"]
        if input_hashes(task) != inputs:
            raise ValueError("Retained study inputs differ from their fingerprints.")
        trusted_scorer = hashlib.sha256((TASK / "tests/score.py").read_bytes()).hexdigest()
        if trusted_scorer != inputs["tests/score.py"]:
            raise ValueError("Use a trusted checkout of the original evaluation code.")
    if score_trials(trials, task) != receipt["answer_checks"]:
        raise ValueError("The raw answers differ from the verified scores or fingerprints.")
    return {"verified": True, "evidence_sha256": evidence_sha256,
            "inputs_verified": "input_sha256" in receipt, "inputs_frozen": frozen_manifest is not None, "answer_checks": receipt["answer_checks"]}


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
