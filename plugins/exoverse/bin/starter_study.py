"""Offline first study shipped with the Exoverse plugin. Python standard library only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import tempfile
from pathlib import Path

SCHEMA = "exoverse.plugin-starter.v1"
PREDICTIONS = ("adaptive", "even", "tie", "skip")
LIMIT = 8192
MEANS = (80, 50, 40)
TRIALS = 300
SEED = 17
QUESTION = "Will adapting to noisy feedback miss fewer expected rewards than sampling evenly?"
PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def measure(adaptive: bool, streams: list[list[int]], *, exploration: int = 200) -> dict:
    pulls = [0] * len(MEANS)
    wins = [0] * len(MEANS)
    for tick in range(TRIALS):
        if not adaptive or tick < len(MEANS):
            arm = tick % len(MEANS)
        else:
            arm = max(range(len(MEANS)), key=lambda i: wins[i] / pulls[i]
                      + math.sqrt(exploration / 100 * math.log(tick) / pulls[i]))
        wins[arm] += streams[arm][pulls[arm]]
        pulls[arm] += 1
    missed = sum(pulls[i] * (max(MEANS) - mean) for i, mean in enumerate(MEANS))
    return {"expected_reward_lost_hundredths": missed, "pulls_by_choice": pulls, "observed_rewards": sum(wins)}


def feedback(seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    return [[int(rng.random() < mean / 100) for _ in range(TRIALS)] for mean in MEANS]


def study(prediction: str = "skip") -> dict:
    if prediction not in PREDICTIONS:
        raise ValueError("Choose adaptive, even, tie, or skip for your prediction.")
    streams = feedback(SEED)
    adaptive, even = measure(True, streams), measure(False, streams)
    gap = even["expected_reward_lost_hundredths"] - adaptive["expected_reward_lost_hundredths"]
    winner = "adaptive" if gap > 0 else "even" if gap < 0 else "tie"
    return {
        "schema": SCHEMA, "question": QUESTION, "prediction": prediction, "seed": SEED,
        "reward_probabilities_percent": list(MEANS), "trials_per_strategy": TRIALS,
        "model_calls": 0, "scope": "one scripted seeded simulation",
        "reference": "https://doi.org/10.1023/A:1013689704352",
        "adaptive": adaptive, "even": even, "lower_expected_loss": winner,
    }


def verified(raw: bytes, expected: str) -> dict:
    if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Receipt bytes do not match the retained SHA-256.")
    try:
        body = json.loads(raw)
        if not isinstance(body, dict) or body.get("schema") != SCHEMA:
            raise ValueError("Choose an Exoverse plugin starter receipt.")
        replay = canonical(study(body.get("prediction")))
    except (UnicodeError, RecursionError) as error:
        raise ValueError("Invalid starter receipt.") from error
    if replay != raw:
        raise ValueError("The study did not reproduce the receipt.")
    return {"verified": True, "sha256": expected, "model_calls": 0}


def run(prediction: str = "skip") -> dict:
    receipt = study(prediction)
    raw = canonical(receipt)
    check = verified(raw, hashlib.sha256(raw).hexdigest())
    return {
        **check, "receipt": receipt,
        "explanation": "Compare lost expected reward across both strategies. Lower is better. "
                       "Both strategies faced the same seeded feedback for each choice. "
                       "This result describes one simulated setting.",
        "next_question": "Would the winner change with fewer trials?",
    }


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exoverse-plugin starter")
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("run", help="run and replay the bundled study")
    start.add_argument("--prediction", choices=PREDICTIONS, default="skip")
    start.add_argument("--out", type=Path, help="write a new receipt file")
    verify = sub.add_parser("verify", help="replay a receipt against its original digest")
    verify.add_argument("file", type=Path)
    verify.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "run":
            report = run(args.prediction)
            if args.out is not None:
                with tempfile.NamedTemporaryFile(dir=args.out.parent) as temporary:
                    temporary.write(canonical(report["receipt"]))
                    temporary.flush()
                    os.link(temporary.name, args.out)
                report["file"] = str(args.out)
        else:
            with args.file.open("rb") as stream:
                report = verified(stream.read(LIMIT + 1), args.sha256)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


TOOLS = (
    {"name": "exoverse_run_first_study", "description": "Run and replay Exoverse's offline first study with no API key.",
     "inputSchema": {"type": "object", "properties": {"prediction": {"enum": list(PREDICTIONS)}},
                     "additionalProperties": False}},
    {"name": "exoverse_verify_first_study", "description": "Reproduce a plugin starter receipt against its SHA-256.",
     "inputSchema": {"type": "object", "required": ["receipt", "sha256"], "properties": {
         "receipt": {"type": "object"}, "sha256": {"type": "string"}}, "additionalProperties": False}},
)


def call(params: dict, enabled: bool) -> dict:
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    name = params.get("name")
    if enabled and isinstance(name, str):
        from paired_study import TOOLS as COMPARISON_TOOLS
        from paired_study import tool_call

        if any(name == tool["name"] for tool in COMPARISON_TOOLS):
            return tool_call(name, arguments)
    if enabled and name == TOOLS[0]["name"] and arguments.keys() <= {"prediction"}:
        return run(arguments.get("prediction", "skip"))
    if enabled and name == TOOLS[1]["name"] and arguments.keys() == {"receipt", "sha256"}:
        if not isinstance(arguments["receipt"], dict) or not isinstance(arguments["sha256"], str):
            raise ValueError("Supply the original receipt object and its SHA-256.")
        return verified(canonical(arguments["receipt"]), arguments["sha256"])
    raise ValueError("Unknown tool or invalid arguments.")


def respond(message: dict, enabled: bool) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    if "id" not in message:
        return None
    reply = {"jsonrpc": "2.0", "id": message["id"]}
    method = message["method"]
    params = message.get("params", {})
    if isinstance(params, dict):
        if method == "initialize":
            version = params.get("protocolVersion")
            return {**reply, "result": {
                "protocolVersion": version if version in PROTOCOLS else PROTOCOLS[-1],
                "capabilities": {"tools": {}}, "serverInfo": {
                    "name": "exoverse-starter" if enabled else "exoverse-runtime-unavailable", "version": "1.0.0"},
                "instructions": ("Use the first study tools to run a local scripted simulation." if enabled else
                                 "The optional Exoverse runtime is unavailable. The starter server works without it."),
            }}
        if method == "ping":
            return {**reply, "result": {}}
        if method == "tools/list":
            from paired_study import TOOLS as COMPARISON_TOOLS

            return {**reply, "result": {"tools": list(TOOLS + COMPARISON_TOOLS) if enabled else []}}
        if method == "tools/call":
            try:
                payload = call(params, enabled)
                return {**reply, "result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}
            except (ValueError, TypeError, RecursionError) as error:
                return {**reply, "result": {"isError": True, "content": [{"type": "text", "text": str(error)}]}}
    return {**reply, "error": {"code": -32601, "message": "Unsupported request"}}


def serve(enabled: bool = True) -> int:
    # A malformed or oversized client frame must not be interpreted as a tool call.
    for raw in iter(lambda: sys.stdin.buffer.readline(65537), b""):
        if len(raw) > 65536:
            return 1
        try:
            reply = respond(json.loads(raw), enabled)
        except (ValueError, RecursionError):
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            print(json.dumps(reply), flush=True)
    return 0
