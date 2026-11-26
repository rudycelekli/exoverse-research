"""Freeze a research protocol and verify a one-variable intervention offline."""

import argparse
import json
import math
import re
from pathlib import Path

from workflow_study import LIMIT, canonical, digest, mapping, name, read

FIELDS = {"question", "hypothesis", "environment", "rubric", "judge", "seeds",
          "budget_microusd", "stopping_rule", "variables"}
SCHEMA = "exoverse.research-spec.v1"


def _reject_constant(value):
    raise ValueError(f"Invalid JSON number: {value}")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Protocol numbers must be finite.")
    return number


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}.")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, parse_constant=_reject_constant, parse_float=_finite_float,
                      object_pairs_hook=_unique_object)


def load(path):
    return decode(read(path))


def load_frozen(path):
    raw = read(path)
    value = decode(raw)
    if canonical(value) != raw:
        raise ValueError("Frozen protocol bytes are not canonical.")
    return value


def protocol(value):
    mapping(value, FIELDS, "Protocol")
    for field in ("question", "hypothesis", "stopping_rule"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"{field} must be nonempty text.")
    for field in ("environment", "rubric"):
        if not isinstance(value[field], dict) or not value[field]:
            raise ValueError(f"{field} must be a nonempty object.")
    if value["judge"] is not None and (not isinstance(value["judge"], dict) or not value["judge"]):
        raise ValueError("judge must be a nonempty object or null.")
    seeds = value["seeds"]
    if (not isinstance(seeds, list) or not seeds or any(type(seed) is not int for seed in seeds)
            or len(seeds) != len(set(seeds))):
        raise ValueError("seeds must be a nonempty list of unique integers.")
    if type(value["budget_microusd"]) is not int or value["budget_microusd"] < 0:
        raise ValueError("budget_microusd must be a nonnegative integer.")
    if not isinstance(value["variables"], dict) or not value["variables"]:
        raise ValueError("Declare at least one study variable.")
    for variable in value["variables"]:
        name(variable)
    return value


def freeze(value, parent=None, variable=None):
    return {"schema": SCHEMA, "protocol": protocol(value), "parent": parent, "changed_variable": variable}


def branch(baseline, fingerprint, variable, replacement):
    mapping(baseline, {"schema", "protocol", "parent", "changed_variable"}, "Frozen baseline")
    if (baseline["schema"] != SCHEMA
            or digest(canonical(baseline)) != fingerprint):
        raise ValueError("Baseline does not match its retained fingerprint.")
    original = protocol(baseline.get("protocol"))
    variables = original["variables"]
    parent, changed = baseline["parent"], baseline["changed_variable"]
    if (parent is None and changed is not None
            or parent is not None and (not isinstance(parent, str) or not re.fullmatch(r"[a-f0-9]{64}", parent)
                                       or not isinstance(changed, str) or changed not in variables)):
        raise ValueError("Baseline lineage metadata is invalid.")
    if variable not in variables or canonical(variables[variable]) == canonical(replacement):
        raise ValueError("Change exactly one declared variable to a different value.")
    return freeze({**original, "variables": {**variables, variable: replacement}}, fingerprint, variable)


def cli(argv):
    parser = argparse.ArgumentParser(prog="exoverse-plugin spec")
    modes = parser.add_subparsers(dest="mode", required=True)
    new = modes.add_parser("freeze")
    new.add_argument("protocol", type=Path)
    new.add_argument("--out", type=Path, required=True)
    for mode in ("branch", "verify"):
        command = modes.add_parser(mode)
        command.add_argument("baseline", type=Path)
        command.add_argument("--parent-sha256", required=True)
        if mode == "branch":
            command.add_argument("variable")
            command.add_argument("replacement", type=Path)
            command.add_argument("--out", type=Path, required=True)
        else:
            command.add_argument("candidate", type=Path)
            command.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "freeze":
            result = freeze(load(args.protocol))
        elif args.mode == "branch":
            result = branch(load_frozen(args.baseline), args.parent_sha256, args.variable, load(args.replacement))
        else:
            supplied = read(args.candidate)
            candidate = decode(supplied)
            variable = candidate["changed_variable"]
            result = branch(load_frozen(args.baseline), args.parent_sha256, variable,
                            candidate["protocol"]["variables"][variable])
            if digest(supplied) != args.candidate_sha256 or canonical(result) != supplied:
                raise ValueError("Candidate fingerprint or single-variable lineage did not reproduce.")
        raw = canonical(result)
        if len(raw) > LIMIT:
            raise ValueError("Frozen protocol exceeds 64 KiB.")
        if args.mode != "verify":
            with args.out.open("xb") as output:
                output.write(raw)
        print(json.dumps({"sha256": digest(raw), "verified": args.mode == "verify"}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
