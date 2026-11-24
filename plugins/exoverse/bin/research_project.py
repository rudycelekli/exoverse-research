"""Portable local project with offline workflow runs and evidence-backed drafts."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from workflow_study import canonical, digest, read, run


def cli(argv):
    parser = argparse.ArgumentParser(prog="exoverse-plugin project")
    parser.add_argument("database", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("init")
    create.add_argument("--question", required=True)
    launch = commands.add_parser("run")
    launch.add_argument("workflow", type=Path)
    commands.add_parser("list")
    draft = commands.add_parser("draft")
    draft.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    try:
        path = args.database.resolve()
        if args.command == "init":
            question = args.question.strip()
            if not question or len(question) > 1000:
                raise ValueError("Enter a research question of 1 to 1000 characters.")
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE project (question TEXT NOT NULL)")
                db.execute("CREATE TABLE studies (digest TEXT PRIMARY KEY, evidence BLOB NOT NULL)")
                db.execute("INSERT INTO project VALUES (?)", (question,))
            result = {"question": question}
        else:
            with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as db, db:
                question, = db.execute("SELECT question FROM project").fetchone()
                if args.command == "run":
                    evidence = canonical(run(json.loads(read(args.workflow))))
                    fingerprint = digest(evidence)
                    db.execute("INSERT OR IGNORE INTO studies VALUES (?, ?)", (fingerprint, evidence))
                    result = {"sha256": fingerprint}
                elif args.command == "list":
                    rows = db.execute("SELECT digest FROM studies ORDER BY rowid")
                    result = {"question": question, "studies": [fingerprint for fingerprint, in rows]}
                else:
                    rows = db.execute("SELECT digest, evidence FROM studies ORDER BY rowid").fetchall()
                    result = {"question": question, "studies": [fingerprint for fingerprint, _ in rows]}
                    export_draft(args.output, question, rows)
                    result["draft"] = str(args.output)
        print(json.dumps(result))
        return 0
    except (OSError, sqlite3.Error, ValueError, TypeError, RecursionError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


def export_draft(output, question, rows):
    if not rows:
        raise ValueError("Run a study before exporting a draft.")
    lines = ["# Research draft", "", "## Research question", "", question, "",
             "## Methods", "", "Deterministic policies were evaluated on the workflow recorded with each study.",
             "Each result was replayed from its saved workflow during export.", "", "## Results", ""]
    for fingerprint, evidence in rows:
        result = json.loads(evidence)
        if (not isinstance(result, dict) or fingerprint != digest(evidence)
                or evidence != canonical(run(result.get("workflow")))):
            raise ValueError("Stored study evidence did not reproduce.")
        lines.extend([f"### Study `{fingerprint}`", "", "```json",
                      json.dumps(result["episodes"], indent=2), "```", ""])
    lines.extend(["## Limitations", "", "Results describe the recorded workflows and policies. "
                  "Generalization and causal claims require separate evidence.", ""])
    with output.open("x", encoding="utf-8") as draft:
        draft.write("\n".join(lines))
