"""Verify a synthetic alignment study and opt in to local review adapters."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import monitor_study
from ifixai_review import VERSION
from paired_study import canonical, digest, read_file, verify

ROW_KEYS = ("case", "ledger_completed", "reported_completed", "baseline_alert", "treatment_alert")


def run_ifixai(python: Path, rows: list[dict], work: Path) -> dict:
    if not python.is_absolute() or not python.is_file():
        raise ValueError("Give the absolute path to an isolated iFixAI Python interpreter.")
    env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "SYSTEMROOT") if key in os.environ}
    work.mkdir(mode=0o700)
    script = Path(__file__).with_name("ifixai_review.py").resolve()
    proc = subprocess.run([str(python), "-I", str(script), str(work)], input=canonical(rows),
                          cwd=work, env=env, capture_output=True, timeout=45, check=False)
    if proc.returncode:
        raise ValueError(f"Local iFixAI audit failed. Check the selected Python contains ifixai=={VERSION}.")
    try:
        audit = json.loads(proc.stdout)
        if audit["version"] != VERSION or not all(
            audit["arms"][arm]["matches_fixture_labels"] is True for arm in ("baseline", "treatment")
        ):
            raise ValueError("iFixAI review disagrees with the fixture labels. Inspect the retained audit reports.")
    except (KeyError, TypeError) as error:
        raise ValueError("The local iFixAI auditor returned an invalid result.") from error
    return audit


def write_new(path: Path, value: dict) -> str:
    raw = canonical(value)
    with path.open("xb") as handle:
        handle.write(raw)
    return digest(raw)


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exoverse-plugin review")
    parser.add_argument("directory", type=Path, help="exported monitor study")
    parser.add_argument("--sha256", required=True, help="independently retained study digest")
    parser.add_argument("--out", required=True, type=Path, help="new review directory")
    parser.add_argument("--ifixai-python", type=Path, help="opt in to the pinned local iFixAI environment")
    parser.add_argument("--ruflo", type=Path, help="opt in to local Ruflo task recording after iFixAI review")
    args = parser.parse_args(argv)
    try:
        if args.ruflo is not None and args.ifixai_python is None:
            raise ValueError("Ruflo task recording requires a completed iFixAI review.")
        raw = read_file(args.directory / "study.json")
        replay = verify(raw, read_file(args.directory / "paper.md").decode(), args.sha256)
        receipt = json.loads(raw)
        if receipt["schema"] != monitor_study.SCHEMA:
            raise ValueError("This review adapter accepts the completion-report monitor template.")
        args.out.mkdir(mode=0o700)
        output = args.out.resolve()
        review = {"schema": "exoverse.plugin-alignment-review.v1", "study": replay,
                  "ifixai": {"status": "disabled"}}
        if args.ifixai_python is not None:
            rows = [{key: row[key] for key in ROW_KEYS} for row in receipt["pairs"]]
            review["ifixai"] = run_ifixai(args.ifixai_python, rows, output / "ifixai")
        seal = write_new(output / "review.json", review)
        result = {**review, "review_sha256": seal, "ruflo": {"status": "disabled"}}
        if args.ruflo is not None:
            from ruflo_review import coordinate

            result["ruflo"] = coordinate(args.ruflo, args.sha256, {"review_sha256": seal}, output)
            write_new(output / "coordination.json", result["ruflo"])
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0
