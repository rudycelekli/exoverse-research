"""Collect paired responses from an existing, trusted local Ollama installation."""

from __future__ import annotations

import argparse
import http.client
import json
import re
from contextlib import ExitStack
from pathlib import Path

import answer_study
from paired_study import LIMIT
from starter_study import canonical

MAX_CASES = 12
MAX_PROMPT_BYTES = 1024
MAX_HTTP_BYTES = 131072
OPTIONS = {"temperature": 0, "seed": 17, "num_predict": 32}
SCHEMA = "exoverse.plugin-local-collection.v1"


class CollectionError(ValueError):
    def __init__(self, message: str, completed: int, case_id: str, arm: str):
        super().__init__(message)
        self.completed = completed
        self.case_id = case_id
        self.arm = arm


def prompt_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > MAX_PROMPT_BYTES:
        raise ValueError("Each prompt must contain 1 to 1024 UTF-8 bytes.")
    return value.strip()


def protocol(cases, model: str, baseline: str, treatment: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,62}:[A-Za-z0-9][A-Za-z0-9._-]{0,62}", model):
        raise ValueError("Use an installed local model with an explicit tag, such as qwen2.5:7b.")
    if "cloud" in model.lower():
        raise ValueError("Select a local model tag for this collection.")
    baseline, treatment = prompt_text(baseline), prompt_text(treatment)
    if baseline == treatment:
        raise ValueError("Provide two different system prompts.")
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError(f"Supply 1 to {MAX_CASES} cases.")
    by_id = answer_study.indexed(cases, ("prompt",), prompt_text)
    return {
        "model": model, "baseline_system": baseline, "treatment_system": treatment,
        "options": dict(OPTIONS),
        "cases": [{"case_id": case_id, "prompt": row[0]} for case_id, row in sorted(by_id.items())],
    }


def request(port: int, path: str, timeout: int, payload: dict | None = None) -> dict:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET" if payload is None else "POST", path,
                           body=None if payload is None else canonical(payload),
                           headers={"Content-Type": "application/json"})
        result = connection.getresponse()
        if result.status != 200:
            raise ValueError(f"Local Ollama returned HTTP {result.status} for {path}.")
        raw = result.read(MAX_HTTP_BYTES + 1)
        if len(raw) > MAX_HTTP_BYTES:
            raise ValueError("Local Ollama returned a response above the size limit.")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("Local Ollama returned an invalid response.")
        return decoded
    except (OSError, http.client.HTTPException, RecursionError) as error:
        raise ValueError(f"Could not complete {path} on local Ollama: {error}") from error
    finally:
        connection.close()


def installed_digest(port: int, model: str, timeout: int) -> str:
    models = request(port, "/api/tags", timeout).get("models")
    if not isinstance(models, list):
        raise ValueError("Local Ollama returned an invalid model inventory.")
    for item in models:
        if isinstance(item, dict) and item.get("name") == model:
            size, details = item.get("size"), item.get("details")
            if (item.get("remote_model") or item.get("remote_host") or type(size) is not int or size <= 0
                    or not isinstance(details, dict) or details.get("format") != "gguf"):
                raise ValueError("Choose a local GGUF model with weights installed.")
            return answer_study.checked_hash(item.get("digest"))
    raise ValueError(f"Model {model} is absent from local Ollama. Install the weights separately.")


def paired_order(spec: dict):
    for index, case in enumerate(spec["cases"]):
        arms = ("baseline", "treatment") if index % 2 == 0 else ("treatment", "baseline")
        yield case, arms


def collect(spec: dict, port: int, timeout: int) -> tuple[list[dict], dict]:
    initial_digest = installed_digest(port, spec["model"], timeout)
    responses = []
    order = []
    for case, arms in paired_order(spec):
        row = {"case_id": case["case_id"]}
        for arm in arms:
            try:
                result = request(port, "/api/generate", timeout, {
                    "model": spec["model"], "prompt": case["prompt"], "system": spec[f"{arm}_system"],
                    "options": spec["options"], "stream": False, "think": False,
                })
                reason = result.get("done_reason")
                if (result.get("model") != spec["model"] or result.get("done") is not True
                        or reason not in ("stop", "length")):
                    raise ValueError("Local generation did not finish normally for the selected model.")
                response = result.get("response")
                answer_study.answer_hash(response)
            except ValueError as error:
                raise CollectionError(str(error), len(order), case["case_id"], arm) from error
            order.append({"case_id": case["case_id"], "arm": arm, "done_reason": reason})
            row[arm] = response
        responses.append(row)
    if installed_digest(port, spec["model"], timeout) != initial_digest:
        raise ValueError("The model digest changed during collection.")
    response_bytes = canonical(responses)
    if len(response_bytes) > LIMIT:
        raise ValueError("Collected responses exceed the scorer's input size limit.")
    return responses, {
        "schema": SCHEMA, "provider": "ollama", "model_digest": initial_digest, "protocol": spec,
        "protocol_sha256": answer_study.fingerprint(spec), "responses_sha256": answer_study.fingerprint(responses),
        "call_order": order, "model_calls": len(order),
    }


def collection_files(responses: list[dict], receipt: dict) -> dict[str, bytes]:
    return {"responses.json": canonical(responses), "collection.json": canonical(receipt)}


def export(directory: Path, files: dict[str, bytes]) -> None:
    directory.mkdir(mode=0o700)
    with ExitStack() as cleanup:
        cleanup.callback(directory.rmdir)
        for name, raw in files.items():
            path = directory / name
            with path.open("xb") as handle:
                cleanup.callback(path.unlink)
                handle.write(raw)
        cleanup.pop_all()


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("cases", type=Path, help="JSON list of case_id and prompt objects")
    parser.add_argument("--model", required=True, help="installed local model and tag")
    parser.add_argument("--baseline-system", required=True)
    parser.add_argument("--treatment-system", required=True)
    parser.add_argument("--port", type=int, default=11434, help="local Ollama port")
    parser.add_argument("--timeout", type=int, default=90, help="seconds per request")
    parser.add_argument("--out", required=True, type=Path, help="new directory for the complete collection")


def prepare(args: argparse.Namespace) -> dict:
    if not 1 <= args.port <= 65535 or not 1 <= args.timeout <= 300:
        raise ValueError("Choose a valid local port and a timeout of 1 to 300 seconds.")
    if args.out.exists() or args.out.is_symlink() or not args.out.parent.is_dir():
        raise ValueError("Choose a new output directory with an existing parent.")
    if not args.cases.is_file():
        raise ValueError("Supply a regular JSON file with cases.")
    with args.cases.open("rb") as handle:
        raw = handle.read(MAX_HTTP_BYTES + 1)
    if len(raw) > MAX_HTTP_BYTES:
        raise ValueError("The cases file exceeds the size limit.")
    return protocol(json.loads(raw), args.model, args.baseline_system, args.treatment_system)


def failed_call(error: CollectionError) -> dict:
    return {"status": "incomplete", "error": str(error), "case_id": error.case_id,
            "arm": error.arm, "successful_calls": error.completed}


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exoverse-plugin collect")
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        spec = prepare(args)
        responses, receipt = collect(spec, args.port, args.timeout)
        export(args.out, collection_files(responses, receipt))
        report = {key: receipt[key] for key in ("model_digest", "model_calls", "protocol_sha256", "responses_sha256")}
        report.update(status="complete", directory=str(args.out), collection_sha256=answer_study.fingerprint(receipt))
    except CollectionError as error:
        print(json.dumps(failed_call(error)))
        return 1
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"status": "incomplete", "error": str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0
