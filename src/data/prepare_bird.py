#!/usr/bin/env python3
"""Convert BIRD Text-to-SQL records to LEAD/Qwen chat JSONL.

This preprocessing step is CPU-only and has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


SYSTEM_PROMPT = (
    "You are a Text-to-SQL assistant. Generate one valid SQL query for the "
    "given database schema and question. Return SQL only, without explanation."
)


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read either a JSON array or one-JSON-object-per-line file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise ValueError("JSON input must contain a list of records")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_schemas(path: Path | None) -> dict[str, dict[str, Any]]:
    """Index BIRD/Spider-style tables.json entries by database ID."""
    if path is None:
        return {}
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {entry["db_id"]: entry for entry in entries}


def render_schema(schema: dict[str, Any] | None) -> str:
    """Render a compact, deterministic schema description for the prompt."""
    if not schema:
        return "Schema unavailable."

    tables = schema.get("table_names_original") or schema.get("table_names") or []
    columns = schema.get("column_names_original") or schema.get("column_names") or []
    types = schema.get("column_types") or ["unknown"] * len(columns)
    table_columns: dict[int, list[str]] = {i: [] for i in range(len(tables))}

    for index, column in enumerate(columns):
        table_index, column_name = column
        if table_index < 0:  # Spider/BIRD uses [-1, "*"] for the wildcard.
            continue
        column_type = types[index] if index < len(types) else "unknown"
        table_columns.setdefault(table_index, []).append(f"{column_name} {column_type}")

    lines = [
        f"CREATE TABLE {table} ({', '.join(table_columns.get(i, []))});"
        for i, table in enumerate(tables)
    ]

    foreign_keys = schema.get("foreign_keys") or []
    for left_index, right_index in foreign_keys:
        try:
            left_table_index, left_column = columns[left_index]
            right_table_index, right_column = columns[right_index]
            lines.append(
                "FOREIGN KEY "
                f"{tables[left_table_index]}.{left_column} -> "
                f"{tables[right_table_index]}.{right_column}"
            )
        except (IndexError, TypeError):
            continue

    return "\n".join(lines) if lines else "Schema unavailable."


def make_user_prompt(record: dict[str, Any], schema_text: str) -> str:
    evidence = str(record.get("evidence") or "").strip()
    parts = [f"Database ID: {record['db_id']}", f"Database schema:\n{schema_text}"]
    if evidence:
        parts.append(f"Evidence:\n{evidence}")
    parts.append(f"Question:\n{str(record['question']).strip()}")
    return "\n\n".join(parts)


def convert_record(
    record: dict[str, Any], index: int, schemas: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    for field in ("db_id", "question"):
        if not record.get(field):
            raise ValueError(f"Record {index} is missing required field: {field}")

    sql = record.get("SQL") or record.get("sql")
    if not sql:
        raise ValueError(f"Record {index} is missing required field: SQL/sql")

    db_id = str(record["db_id"])
    schema_text = render_schema(schemas.get(db_id))
    example_id = str(record.get("id") or f"bird_{index:06d}_{db_id}")

    return {
        "dataset": "bird",
        "id": example_id,
        "db_id": db_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": make_user_prompt(record, schema_text)},
            {"role": "assistant", "content": str(sql).strip()},
        ],
    }


def convert_records(
    records: Iterable[dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    selected = list(records)
    if max_records is not None:
        selected = selected[:max_records]
    return [convert_record(record, index, schemas) for index, record in enumerate(selected)]


def write_jsonl(records: Iterable[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="BIRD JSON or JSONL file")
    parser.add_argument(
        "--tables-json",
        type=Path,
        default=None,
        help="Optional BIRD/Spider-style tables.json containing database schemas",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output chat JSONL")
    parser.add_argument("--max-records", type=int, default=None, help="Only convert the first N rows")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_records(args.input)
    schemas = load_schemas(args.tables_json)
    converted = convert_records(records, schemas, args.max_records)
    write_jsonl(converted, args.output)
    missing_schema = sum(item["db_id"] not in schemas for item in converted)
    print(f"Converted {len(converted)} records -> {args.output}")
    if missing_schema:
        print(f"Warning: {missing_schema} records were converted without schema details")


if __name__ == "__main__":
    main()
