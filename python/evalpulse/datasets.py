import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDataset:
    cases: list[dict[str, Any]]
    digest: str
    schema: dict[str, Any]


def parse_dataset(content: str, source_format: str, max_bytes: int, max_rows: int) -> ParsedDataset:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        raise DatasetValidationError(f"Dataset exceeds {max_bytes} bytes")
    if source_format == "json":
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(f"Invalid JSON at line {exc.lineno}") from exc
        if not isinstance(raw, list):
            raise DatasetValidationError("JSON dataset must be an array")
        rows = raw
    elif source_format == "csv":
        rows = list(csv.DictReader(io.StringIO(content)))
    else:
        raise DatasetValidationError("Unsupported dataset format")
    if not rows:
        raise DatasetValidationError("Dataset must contain at least one case")
    if len(rows) > max_rows:
        raise DatasetValidationError(f"Dataset exceeds {max_rows} rows")

    cases: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise DatasetValidationError(f"Row {index + 1} must be an object")
        if source_format == "csv":
            row = _normalize_csv_row(row, index)
        case_input = row.get("input")
        if not isinstance(case_input, dict):
            raise DatasetValidationError(f"Row {index + 1} input must be an object")
        tags = row.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise DatasetValidationError(f"Row {index + 1} tags must be an array of strings")
        cases.append({"input": case_input, "expected": row.get("expected"), "tags": tags})
    fields = sorted({key for case in cases for key in case["input"]})
    return ParsedDataset(
        cases=cases,
        digest=hashlib.sha256(encoded).hexdigest(),
        schema={"input_fields": fields, "case_count": len(cases)},
    )


def _normalize_csv_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    try:
        parsed_input = json.loads(row.get("input", ""))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Row {index + 1} has invalid input JSON") from exc
    expected_raw = row.get("expected")
    try:
        expected = json.loads(expected_raw) if expected_raw else None
    except json.JSONDecodeError:
        expected = expected_raw
    tags = [tag.strip() for tag in (row.get("tags") or "").split("|") if tag.strip()]
    return {"input": parsed_input, "expected": expected, "tags": tags}
