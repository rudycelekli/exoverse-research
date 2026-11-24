"""Compare two declarative policies in independent finite-state workflows."""

import argparse
import json
import re
from pathlib import Path

from paired_study import digest
from starter_study import canonical

LIMIT = 65536
SCHEMA = "exoverse.workflow-study.v1"
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}")


def mapping(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} needs exactly: {', '.join(sorted(fields))}.")
    return value


def name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("Use identifiers containing letters, digits, hyphens or underscores.")
    return value


def read(path):
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("File exceeds 64 KiB.")
    return raw


def run(spec):
    mapping(spec, {"initial", "states", "criteria", "policies", "max_steps"}, "Workflow")
    states = spec["states"]
    if not isinstance(states, dict) or not 2 <= len(states) <= 32:
        raise ValueError("Define 2 to 32 states.")
    initial = name(spec["initial"])
    if initial not in states:
        raise ValueError("The initial state must exist.")
    ceiling = spec["max_steps"]
    if type(ceiling) is not int or not 1 <= ceiling <= 30:
        raise ValueError("Set max_steps between 1 and 30.")
    for state, actions in states.items():
        name(state)
        if not isinstance(actions, dict) or len(actions) > 12:
            raise ValueError("Each state needs a map of at most 12 actions.")
        for action, target in actions.items():
            name(action)
            if name(target) not in states:
                raise ValueError("Every action must lead to a declared state.")
    criteria = mapping(spec["criteria"], {"goal", "within_steps"}, "Criteria")
    goal = name(criteria["goal"])
    deadline = criteria["within_steps"]
    if goal not in states or states[goal] or goal == initial:
        raise ValueError("The goal must be a terminal state distinct from the initial state.")
    if type(deadline) is not int or not 1 <= deadline <= ceiling:
        raise ValueError("Set within_steps between 1 and max_steps.")

    policies = spec["policies"]
    if not isinstance(policies, dict) or len(policies) != 2:
        raise ValueError("Supply two named policies.")
    episodes = {}
    for label, policy in policies.items():
        name(label)
        if not isinstance(policy, dict):
            raise ValueError("Each policy maps states to allowed actions.")
        if policy.keys() != {state for state, actions in states.items() if actions}:
            raise ValueError("Each policy must choose an action for every nonterminal state.")
        for state, action in policy.items():
            if name(action) not in states[state]:
                raise ValueError("A policy selected an undeclared action.")

        state, trace = initial, []
        while states[state] and len(trace) < ceiling:
            action = policy[state]
            target = states[state][action]
            reward = int(target == goal and len(trace) + 1 <= deadline)
            trace.append({"state": state, "action": action, "next_state": target, "reward": reward})
            state = target
        episodes[label] = {"trace": trace, "final_state": state, "terminated": not states[state],
                           "truncated": bool(states[state]), "success": state == goal and len(trace) <= deadline,
                           "reward": sum(step["reward"] for step in trace)}
    return {"schema": SCHEMA, "workflow": spec, "episodes": episodes, "model_calls": 0}


def cli(argv):
    parser = argparse.ArgumentParser(prog="exoverse-plugin workflow")
    sub = parser.add_subparsers(dest="mode", required=True)
    launch = sub.add_parser("run")
    launch.add_argument("spec", type=Path)
    launch.add_argument("--out", required=True, type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("evidence", type=Path)
    verify.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "run":
            result = run(json.loads(read(args.spec)))
            raw = canonical(result)
            if len(raw) > LIMIT:
                raise ValueError("Evidence exceeds 64 KiB.")
            with args.out.open("xb") as out:
                out.write(raw)
        else:
            raw = read(args.evidence)
            if digest(raw) != args.sha256:
                raise ValueError("Evidence does not match the retained fingerprint.")
            result = json.loads(raw)
            if not isinstance(result, dict) or canonical(run(result.get("workflow"))) != raw:
                raise ValueError("The workflow evidence did not reproduce.")
        print(json.dumps({"sha256": digest(raw), "verified": args.mode == "verify",
                          "episodes": result["episodes"], "model_calls": 0}, indent=2))
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 0
