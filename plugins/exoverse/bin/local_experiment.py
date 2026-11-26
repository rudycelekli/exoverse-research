"""Run and verify a local experiment linking collection to its scored paper."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import answer_study
import local_collection
import observed_study
import paired_study
from starter_study import canonical

SCHEMA = "exoverse.plugin-local-experiment.v1"
FILES = ("collection.json", "responses.json", "study.json", "paper.md")


def score(metadata: dict, key: dict, key_sha256: str, responses: list) -> dict:
    return paired_study.run(answer_study.from_answers({
        **metadata, "key": key, "key_sha256": key_sha256, "responses": responses,
    }))


def verify_collection(receipt: dict, responses: list, raw_responses: bytes) -> None:
    if not isinstance(receipt, dict) or receipt.get("schema") != local_collection.SCHEMA:
        raise ValueError("Choose a local collection receipt.")
    spec = receipt["protocol"]
    restored = local_collection.protocol(
        spec["cases"], spec["model"], spec["baseline_system"], spec["treatment_system"],
    )
    if (receipt["provider"] != "ollama" or spec != restored
            or receipt["protocol_sha256"] != answer_study.fingerprint(restored)
            or receipt["responses_sha256"] != paired_study.digest(raw_responses)):
        raise ValueError("The collection does not match its recorded protocol or responses.")
    answer_study.checked_hash(receipt["model_digest"])
    case_ids = [row["case_id"] for row in restored["cases"]]
    if [row["case_id"] for row in responses] != case_ids:
        raise ValueError("Responses do not match the collected cases in order.")
    expected_order = [(case["case_id"], arm) for case, arms in local_collection.paired_order(restored) for arm in arms]
    calls = receipt["call_order"]
    if ([(row["case_id"], row["arm"]) for row in calls] != expected_order
            or any(row["done_reason"] not in ("stop", "length") for row in calls)
            or receipt["model_calls"] != len(expected_order)):
        raise ValueError("The collection does not contain a complete paired call record.")


def verified(files: dict[str, bytes]) -> dict:
    responses = json.loads(files["responses.json"])
    collection = json.loads(files["collection.json"])
    study = json.loads(files["study.json"])
    verify_collection(collection, responses, files["responses.json"])
    if study.get("schema") != answer_study.SCHEMA:
        raise ValueError("The experiment needs a scored answer-key study.")
    spec = study["protocol"]
    metadata = {field: spec[field] for field in answer_study.METADATA_FIELDS}
    replay = score(metadata, spec["key"], spec["key_sha256"], responses)
    if canonical(replay["receipt"]) != files["study.json"] or replay["paper"].encode() != files["paper.md"]:
        raise ValueError("The scored study and paper do not match the collected responses.")
    return {"verified": True, "study_sha256": replay["sha256"], "key_sha256": spec["key_sha256"],
            "collected_model_calls": collection["model_calls"], "verification_model_calls": 0,
            "model_digest": collection["model_digest"], "pairs": replay["pairs"]}


def experiment(args: argparse.Namespace) -> dict:
    spec = local_collection.prepare(args)
    key = paired_study.read_json_file(args.key)
    metadata = {field: getattr(args, field) for field in answer_study.METADATA_FIELDS}
    observed_study.normalize_metadata(**metadata, metric=answer_study.METRIC)
    expected = answer_study.validate_key(key, args.key_sha256)
    if expected.keys() != {case["case_id"] for case in spec["cases"]}:
        raise ValueError("The answer key IDs must match the experiment cases before collecting responses.")
    responses, collection = local_collection.collect(spec, args.port, args.timeout)
    scored = score(metadata, key, args.key_sha256, responses)
    files = local_collection.collection_files(responses, collection)
    files.update({"study.json": canonical(scored["receipt"]), "paper.md": scored["paper"].encode()})
    report = verified(files)
    seal = canonical({"schema": SCHEMA, "files": {name: paired_study.digest(raw) for name, raw in files.items()}})
    local_collection.export(args.out, {**files, "experiment.json": seal})
    return {**report, "experiment_sha256": paired_study.digest(seal), "directory": str(args.out)}


def verify(directory: Path, expected: str) -> dict:
    answer_study.checked_hash(expected)
    manifest_raw = paired_study.read_file(directory / "experiment.json")
    if paired_study.digest(manifest_raw) != expected:
        raise ValueError("The experiment does not match the retained fingerprint.")
    manifest = json.loads(manifest_raw)
    if (not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA
            or not isinstance(manifest.get("files"), dict) or manifest["files"].keys() != set(FILES)):
        raise ValueError("The experiment manifest is invalid.")
    files = {}
    for name in FILES:
        limit = local_collection.MAX_HTTP_BYTES if name == "collection.json" else paired_study.LIMIT
        raw = paired_study.read_file(directory / name, limit)
        if len(raw) > limit or paired_study.digest(raw) != manifest["files"][name]:
            raise ValueError(f"{name} does not match the experiment fingerprint.")
        files[name] = raw
    return {**verified(files), "experiment_sha256": expected}


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exoverse-plugin experiment")
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="collect both arms and save a locally verified scored bundle")
    local_collection.add_arguments(run)
    run.add_argument("--key", required=True, type=Path)
    run.add_argument("--key-sha256", required=True)
    for field in answer_study.METADATA_FIELDS:
        run.add_argument("--" + field.replace("_", "-"), required=True)
    check = sub.add_parser("verify", help="verify the entire experiment offline")
    check.add_argument("directory", type=Path)
    check.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = experiment(args) if args.action == "run" else verify(args.directory, args.sha256)
    except local_collection.CollectionError as error:
        print(json.dumps(local_collection.failed_call(error)))
        return 1
    except (AttributeError, KeyError, TypeError, ValueError, OSError, RecursionError) as error:
        print(json.dumps({"verified": False, "error": str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0
