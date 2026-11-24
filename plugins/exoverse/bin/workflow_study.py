"""Compare two declarative policies in independent finite-state workflows."""

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from paired_study import digest
from starter_study import canonical

LIMIT = 65536
SCHEMA = "exoverse.workflow-study.v1"
LIVE_SCHEMA = "exoverse.live-workflow-study.v1"
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


def run(spec, controllers=None):
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
    criteria = spec["criteria"]
    required = {"goal", "within_steps"}
    optional = {"required_states", "forbidden_states"}
    if not isinstance(criteria, dict) or not required <= criteria.keys() <= required | optional:
        raise ValueError("Criteria needs a goal and deadline, with optional required and forbidden states.")
    rubric = {}
    for field in optional:
        items = criteria.get(field, [])
        if not isinstance(items, list) or len(items) > 32:
            raise ValueError("State criteria must be lists of at most 32 declared states.")
        rubric[field] = {name(item) for item in items}
        if len(items) != len(rubric[field]) or not rubric[field] <= states.keys():
            raise ValueError("State criteria must contain unique, declared states.")
    if rubric["required_states"] & rubric["forbidden_states"]:
        raise ValueError("A state cannot be both required and forbidden.")
    checks_enabled = bool(optional & criteria.keys())
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
        visited = {initial}
        while states[state] and len(trace) < ceiling:
            action = policy[state] if controllers is None else controllers[label]({
                "state": state, "allowed_actions": sorted(states[state]), "goal": goal,
                "remaining_steps": ceiling - len(trace), "deadline": deadline, "trace": trace,
            })
            if not isinstance(action, str) or action not in states[state]:
                raise ValueError("The recorded action is outside the allowed workflow choices.")
            target = states[state][action]
            visited.add(target)
            checks = rubric["required_states"] <= visited and not rubric["forbidden_states"] & visited
            reward = int(target == goal and len(trace) + 1 <= deadline and checks)
            trace.append({"state": state, "action": action, "next_state": target, "reward": reward})
            state = target
        episodes[label] = {"trace": trace, "final_state": state, "terminated": not states[state],
                           "truncated": bool(states[state]), "success": any(step["reward"] for step in trace),
                           "reward": sum(step["reward"] for step in trace)}
        if checks_enabled:
            episodes[label]["criteria"] = {
                "goal_reached": state == goal,
                "within_deadline": len(trace) <= deadline,
                "missing_required_states": sorted(rubric["required_states"] - visited),
                "visited_forbidden_states": sorted(rubric["forbidden_states"] & visited),
            }
    return {"schema": SCHEMA, "workflow": spec, "episodes": episodes, "model_calls": 0}


def live_spec(spec):
    mapping(spec, {"initial", "states", "criteria", "max_steps"}, "Live workflow")
    if not isinstance(spec["states"], dict):
        raise ValueError("Provide a state map.")
    placeholder = {}
    for state, actions in spec["states"].items():
        if not isinstance(actions, dict):
            raise ValueError("Every state needs an action map.")
        if actions:
            placeholder[state] = min(actions)
    prepared = {**spec, "policies": {"claude": placeholder, "codex": placeholder}}
    run(prepared)
    return prepared


def live_result(prepared, controllers, versions):
    mapping(versions, {"claude", "codex"}, "Agent versions")
    if any(not isinstance(version, str) or not version or len(version) > 160 for version in versions.values()):
        raise ValueError("Invalid agent version.")
    outcome = run(prepared, controllers)
    return {"schema": LIVE_SCHEMA, "workflow": {key: value for key, value in prepared.items() if key != "policies"},
            "agent_versions": versions, "episodes": outcome["episodes"],
            "agent_invocations": sum(len(row["trace"]) for row in outcome["episodes"].values())}


def replay_live(receipt):
    prepared = live_spec(receipt["workflow"])
    traces = mapping(receipt["episodes"], {"claude", "codex"}, "Recorded agents")

    def replay(label):
        def action(observation):
            trace = traces[label]["trace"]
            index = len(observation["trace"])
            if index >= len(trace):
                raise ValueError("The recorded trajectory ended before the workflow.")
            return trace[index]["action"]
        return action

    return live_result(prepared, {label: replay(label) for label in traces}, receipt["agent_versions"])


def run_live(args):
    from workflow_agents import connector

    prepared = live_spec(json.loads(read(args.spec)))
    if not args.allow_model_calls or not 2 * prepared["max_steps"] <= args.max_calls <= 60:
        raise ValueError("Live execution requires --allow-model-calls and an invocation cap covering both arms.")
    if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
        raise ValueError("Choose a new output file in an existing directory before running agents.")
    with TemporaryDirectory(prefix="exoverse-claude-") as claude, TemporaryDirectory(prefix="exoverse-codex-") as codex:
        controllers, versions = {}, {}
        for name, folder in (("claude", claude), ("codex", codex)):
            controllers[name], versions[name] = connector(name, Path(folder))
        return live_result(prepared, controllers, versions)


def cli(argv):
    parser = argparse.ArgumentParser(prog="exoverse-plugin workflow")
    sub = parser.add_subparsers(dest="mode", required=True)
    launch = sub.add_parser("run")
    launch.add_argument("spec", type=Path)
    launch.add_argument("--out", required=True, type=Path)
    live = sub.add_parser("live")
    live.add_argument("spec", type=Path)
    live.add_argument("--out", required=True, type=Path)
    live.add_argument("--allow-model-calls", action="store_true")
    live.add_argument("--max-calls", type=int, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("evidence", type=Path)
    verify.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode in {"run", "live"}:
            result = run_live(args) if args.mode == "live" else run(json.loads(read(args.spec)))
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
            if not isinstance(result, dict):
                raise ValueError("Expected workflow evidence.")
            replayed = replay_live(result) if result.get("schema") == LIVE_SCHEMA else run(result.get("workflow"))
            if canonical(replayed) != raw:
                raise ValueError("The workflow evidence did not reproduce.")
        print(json.dumps({"sha256": digest(raw), "verified": args.mode == "verify",
                          "episodes": result["episodes"],
                          **({"agent_invocations": result["agent_invocations"]} if result["schema"] == LIVE_SCHEMA else {}),
                          **({"model_calls": 0} if args.mode != "live" else {})}, indent=2))
    except (OSError, ValueError, RecursionError, TypeError, KeyError, AttributeError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    return 0
