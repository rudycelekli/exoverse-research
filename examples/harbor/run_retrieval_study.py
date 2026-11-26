"""Run the frozen retrieval comparison using Python from the Harbor environment."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

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
    cli("harbor", "verify", evidence, "--sha256", report["sha256"], "--draft", output / "paper.md")
    (output / "verification.json").write_text(json.dumps({"evidence_sha256": report["sha256"],
                                                          "answer_checks": checks}, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
