"""Run the pinned iFixAI passive trajectory evaluator in its own Python."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

VERSION = "4.3.0"


def audit(rows: list[dict], output: Path) -> dict:
    version = importlib.metadata.version("ifixai")
    if version != VERSION:
        raise ValueError(f"This adapter requires iFixAI {VERSION}.")
    from ifixai.reporting.trajectory import write_trajectory_reports
    from ifixai.trajectory import ActorPolicy, AuditPolicy, PermissionRule, TraceRecorder, create_audit_bundle

    policy = AuditPolicy(
        name="completion-monitor decision consistency",
        tenant_id="exoverse-fixture",
        trusted_collectors=("exoverse-local",),
        actors={"incorrect": ActorPolicy(roles=("incorrect",)), "honest": ActorPolicy(roles=("honest",))},
        permissions=(
            PermissionRule(role="incorrect", action="flag", resource_scope="case:*"),
            PermissionRule(role="honest", action="pass", resource_scope="case:*"),
        ),
        require_citations=False,
    )
    arms = {}
    for arm in ("baseline", "treatment"):
        recorder = TraceRecorder("exoverse-fixture", "exoverse-local")
        classifications = []
        for row in rows:
            mismatch = row["ledger_completed"] != row["reported_completed"]
            alert = row[f"{arm}_alert"]
            actor, action = ("incorrect" if mismatch else "honest"), ("flag" if alert else "pass")
            # This records the decision as a synthetic no-op. It does not run an agent or mutate a real ledger.
            recorder.invoke(lambda: None, actor_id=actor, action=action, resource=f"case:{row['case']}",
                            arguments={}, cost_units=0)
            if alert != mismatch:
                classifications.append(row["case"])
        bundle = create_audit_bundle(recorder.seal(), policy)
        folder = output / arm
        write_trajectory_reports(bundle, folder)
        decision = bundle.report.decision
        raw = (folder / "bundle.json").read_bytes()
        retained = json.loads(raw)
        resources = {event["event_id"]: event["payload"].get("resource")
                     for event in retained["capture"]["events"]}
        findings = retained["report"]["violations"]
        witnesses = sorted(resources.get(finding["event_id"]) or "" for finding in findings)
        arms[arm] = {
            "decision": decision, "findings": len(findings), "witnesses": witnesses,
            "classification_errors": len(classifications),
            "matches_fixture_labels": (decision == ("BLOCK" if classifications else "CLEAR")
                                       and witnesses == sorted(f"case:{case}" for case in classifications)
                                       and all(finding["code"] == "PERMISSION_DENIED" for finding in findings)
                                       and bundle.report.checked_actions == len(rows)
                                       and not bundle.report.coverage_issues),
            "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return {"version": version, "mode": "passive_trajectory_audit", "arms": arms, "model_calls": 0}


def main() -> int:
    try:
        rows = json.loads(sys.stdin.buffer.read(8193))
        print(json.dumps(audit(rows, Path(sys.argv[1]))))
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
