"""Analyze researcher-supplied matched scores without executing their source."""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal

SCHEMA = "exoverse.plugin-observed-pairs.v1"
MAX_PAIRS = 50
MAX_SCORE = 999_999_999
COLUMNS = ("case_id", "baseline", "treatment")
TEXT_LIMITS = {"question": 240, "metric": 80, "baseline_label": 80, "treatment_label": 80}
FIELDS = set(TEXT_LIMITS) | {"rows"}


def read_csv(raw: bytes) -> list[dict]:
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    rows = []
    try:
        if next(reader, []) != list(COLUMNS):
            raise ValueError("Use the CSV header case_id,baseline,treatment.")
        for line in reader:
            if len(line) != len(COLUMNS):
                raise ValueError(f"CSV line {reader.line_num} must include a case ID and both scores.")
            case_id, baseline, treatment = line
            if any(not re.fullmatch(r"[+-]?[0-9]{1,9}", score) for score in (baseline, treatment)):
                raise ValueError(f"CSV line {reader.line_num} must contain two integer scores.")
            rows.append({"case_id": case_id, "baseline": int(baseline), "treatment": int(treatment)})
            if len(rows) > MAX_PAIRS:
                raise ValueError(f"Supply at most {MAX_PAIRS} matched cases.")
    except csv.Error as error:
        raise ValueError(f"Invalid CSV at line {reader.line_num}: {error}") from error
    return rows


def normalize_metadata(question: str, metric: str, baseline_label: str, treatment_label: str) -> dict:
    text = dict(question=question, metric=metric, baseline_label=baseline_label, treatment_label=treatment_label)
    for name, value in text.items():
        limit = TEXT_LIMITS[name]
        if not isinstance(value, str) or not value.strip() or not value.isprintable() or len(value) > limit:
            raise ValueError(f"Provide {name} as a printable line of at most {limit} characters.")
        text[name] = value.strip()
    if text["baseline_label"] == text["treatment_label"]:
        raise ValueError("Give the two arms different labels.")
    return text


def compare(question: str, metric: str, baseline_label: str, treatment_label: str, rows: list) -> dict:
    text = normalize_metadata(question, metric, baseline_label, treatment_label)
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_PAIRS:
        raise ValueError(f"Supply 1 to {MAX_PAIRS} matched cases.")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() != set(COLUMNS):
            raise ValueError("Each case needs an ID, baseline score, and treatment score.")
        case_id = row["case_id"]
        if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", case_id):
            raise ValueError("Use case IDs of up to 64 letters, digits, periods, underscores or hyphens.")
        if case_id in seen:
            raise ValueError(f"Duplicate case ID: {case_id}.")
        seen.add(case_id)
        if any(type(row[name]) is not int or abs(row[name]) > MAX_SCORE for name in COLUMNS[1:]):
            raise ValueError("Use integer scores between -999999999 and 999999999.")

    ordered = sorted(rows, key=lambda row: row["case_id"])
    deltas = [row["treatment"] - row["baseline"] for row in ordered]
    return {
        "schema": SCHEMA,
        "protocol": {"template": "observed", **text, "rows": ordered},
        "pairs": [{"delta": delta} for delta in deltas],
        "total_delta": sum(deltas),
        "treatment_higher": sum(delta > 0 for delta in deltas),
        "treatment_lower": sum(delta < 0 for delta in deltas),
        "ties": deltas.count(0),
        "model_calls": 0,
    }


def paper(
    receipt: dict, seal: str, *, rows: list[dict] | None = None,
    title: str = "Paired analysis of supplied scores",
    method: str = "Match scores by case ID and subtract baseline from treatment for each case.",
    scope: str = ("The researcher supplied these scores. Verification recomputes the analysis\n"
                  "from those scores. It does not establish how the scores were collected,\n"
                  "whether the comparison was causal, or whether higher scores are better."),
    key_sha256: str = "",
) -> str:
    spec = receipt["protocol"]
    pairs = receipt["pairs"]
    if rows is None:
        rows = spec["rows"]
    key_line = f"- Answer key SHA-256: `{key_sha256}`\n" if key_sha256 else ""
    mean = Decimal(receipt["total_delta"]) / len(pairs)
    table = "\n".join(
        f"| {row['case_id']} | {row['baseline']} | {row['treatment']} | {pairs[index]['delta']:+d} |"
        for index, row in enumerate(rows)
    )
    return f"""# {title}

## Research question

    {spec['question']}

## Method

{method}

    Metric: {spec['metric']}
    Baseline: {spec['baseline_label']}
    Treatment: {spec['treatment_label']}

## Results

| Case | Baseline | Treatment | Treatment minus baseline |
| --- | ---: | ---: | ---: |
{table}

Across {len(pairs)} matched cases, the mean difference was **{mean:+.3f}** (rounded).
Treatment scored higher on {receipt['treatment_higher']} cases, lower on
{receipt['treatment_lower']}, and tied on {receipt['ties']}.

## Scope

{scope}
No model was called during this analysis.

## Reproduce

Run `exoverse-plugin paired reproduce PATH --sha256 {seal} --out reproduced-study`.

- Evidence SHA-256: `{seal}`
- Protocol SHA-256: `{receipt['protocol_sha256']}`
{key_line}"""
