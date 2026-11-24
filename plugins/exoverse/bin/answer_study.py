"""Lock reference answers and compare two sets of responses by exact match."""

from __future__ import annotations

import hashlib
import re
import unicodedata

import observed_study
from starter_study import canonical

SCHEMA = "exoverse.plugin-exact-match.v1"
KEY_SCHEMA = "exoverse.plugin-answer-key.v1"
MAX_ANSWER_BYTES = 128
MAX_RESPONSE_BYTES = 1024
KEY_TOOL = "exoverse_create_answer_key"
SCORE_TOOL = "exoverse_score_paired_answers"
METRIC = "exact match (0 or 1)"
METADATA_FIELDS = ("question", "baseline_label", "treatment_label")
SCORE_FIELDS = {*METADATA_FIELDS, "key", "key_sha256", "responses"}

CASE_ID = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
SHA256 = r"[a-f0-9]{64}"


def fingerprint(key: dict | list) -> str:
    return hashlib.sha256(canonical(key)).hexdigest()


def answer_hash(value: str, *, reference: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("Each answer must be text.")
    normalized = unicodedata.normalize("NFC", value.strip())
    if reference:
        if not normalized.isprintable() or len(normalized.encode()) > MAX_ANSWER_BYTES:
            raise ValueError("Use single-line reference answers of at most 128 UTF-8 bytes.")
    elif len(value.encode()) > MAX_RESPONSE_BYTES:
        raise ValueError("Use responses of at most 1024 UTF-8 bytes.")
    return hashlib.sha256(normalized.encode()).hexdigest()


def indexed(rows: list, columns: tuple[str, ...], convert) -> dict:
    if not isinstance(rows, list) or not 1 <= len(rows) <= observed_study.MAX_PAIRS:
        raise ValueError("Supply 1 to 50 cases.")
    fields = {"case_id", *columns}
    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.keys() != fields:
            raise ValueError("Each row must contain " + ", ".join(sorted(fields)) + ".")
        case_id = row["case_id"]
        if not isinstance(case_id, str) or not re.fullmatch(CASE_ID, case_id):
            raise ValueError("Use case IDs of up to 64 letters, digits, periods, underscores or hyphens.")
        if case_id in result:
            raise ValueError(f"Duplicate case ID: {case_id}.")
        result[case_id] = tuple(convert(row[column]) for column in columns)
    return result


def create_key(references: list) -> dict:
    by_case = indexed(references, ("expected",), lambda value: answer_hash(value, reference=True))
    key = {"schema": KEY_SCHEMA, "cases": {case_id: item[0] for case_id, item in sorted(by_case.items())}}
    return {"key": key, "sha256": fingerprint(key), "cases": len(by_case), "model_calls": 0}


def checked_hash(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(SHA256, value):
        raise ValueError("Expected a lowercase SHA-256 fingerprint.")
    return value


def validate_key(key: dict, key_sha256: str) -> dict:
    checked_hash(key_sha256)
    if (not isinstance(key, dict) or key.keys() != {"schema", "cases"} or key["schema"] != KEY_SCHEMA
            or not isinstance(key["cases"], dict) or not 1 <= len(key["cases"]) <= observed_study.MAX_PAIRS):
        raise ValueError("Supply an Exoverse answer key.")
    expected = key["cases"]
    for case_id, value in expected.items():
        if not isinstance(case_id, str) or not re.fullmatch(CASE_ID, case_id):
            raise ValueError("The answer key contains an invalid case ID.")
        checked_hash(value)
    if fingerprint(key) != key_sha256:
        raise ValueError("The answer key does not match its retained fingerprint.")
    return expected


def score_rows(key: dict, key_sha256: str, responses: list) -> list[dict]:
    expected = validate_key(key, key_sha256)
    actual = indexed(responses, ("baseline", "treatment"), checked_hash)
    if expected.keys() != actual.keys():
        raise ValueError("Response IDs must match the answer key exactly.")
    return [
        {"case_id": case_id, "baseline": int(baseline == expected[case_id]),
         "treatment": int(treatment == expected[case_id])}
        for case_id, (baseline, treatment) in sorted(actual.items())
    ]


def from_answers(spec: dict) -> dict:
    responses = indexed(spec["responses"], ("baseline", "treatment"), answer_hash)
    return {**spec, "template": "answer_key", "metric": METRIC, "responses": [
        {"case_id": case_id, "baseline": baseline, "treatment": treatment}
        for case_id, (baseline, treatment) in sorted(responses.items())
    ]}


def compare(question: str, metric: str, baseline_label: str, treatment_label: str,
            key: dict, key_sha256: str, responses: list) -> dict:
    if metric != METRIC:
        raise ValueError("The metric for this study must be exact match.")
    rows = score_rows(key, key_sha256, responses)
    receipt = observed_study.compare(question, metric, baseline_label, treatment_label, rows)
    metadata = {name: receipt["protocol"][name] for name in observed_study.TEXT_LIMITS}
    return {**receipt, "schema": SCHEMA, "protocol": {
        "template": "answer_key", **metadata, "key": key, "key_sha256": key_sha256,
        "responses": sorted(responses, key=lambda row: row["case_id"]),
    }}


def paper(receipt: dict, seal: str) -> str:
    spec = receipt["protocol"]
    rows = score_rows(spec["key"], spec["key_sha256"], spec["responses"])
    return observed_study.paper(
        receipt, seal, rows=rows, title="Paired exact-match study",
        method="Score each response 1 if its normalized SHA-256 matches the locked reference and 0 otherwise.",
        scope=("The source answers were supplied by the researcher. Replay verifies the fingerprinted key, "
               "answer hash comparisons, and arithmetic. It does not verify the origin of the answer strings "
               "or when the key was locked. Hashes of predictable answers can be guessed."),
        key_sha256=spec["key_sha256"],
    )


def row_schema(*columns: str) -> dict:
    return {"type": "array", "minItems": 1, "maxItems": observed_study.MAX_PAIRS, "items": {
        "type": "object", "additionalProperties": False, "required": ["case_id", *columns],
        "properties": {"case_id": {"type": "string", "pattern": "^" + CASE_ID + "$"},
                       **{column: {"type": "string",
                                   "maxLength": MAX_ANSWER_BYTES if column == "expected" else MAX_RESPONSE_BYTES}
                          for column in columns}},
    }}


TOOLS = (
    {"name": KEY_TOOL, "description": "Hash a reference answer key. Retain its fingerprint before collecting responses.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["references"],
                     "properties": {"references": row_schema("expected")}}},
    {"name": SCORE_TOOL, "description": "Score two sets of supplied answers against a retained exact-match key.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": sorted(SCORE_FIELDS),
                     "properties": {
                         **{field: {"type": "string", "maxLength": observed_study.TEXT_LIMITS[field]}
                            for field in METADATA_FIELDS},
                         "key": {"type": "object"}, "key_sha256": {"type": "string", "pattern": "^" + SHA256 + "$"},
                         "responses": row_schema("baseline", "treatment"),
                     }}},
)
