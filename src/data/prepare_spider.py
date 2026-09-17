#!/usr/bin/env python3
"""Convert Spider 1.0 examples into compact CodeT5 text-to-text JSONL."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


def read_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return value


def load_schemas(path: Path) -> dict[str, dict[str, Any]]:
    return {row["db_id"]: row for row in read_json(path)}


def render_schema(schema: dict[str, Any]) -> str:
    """Render table/column names compactly enough for a small local model."""
    tables = schema.get("table_names_original") or schema.get("table_names") or []
    columns = schema.get("column_names_original") or schema.get("column_names") or []
    grouped: dict[int, list[str]] = {index: [] for index in range(len(tables))}
    for table_index, column_name in columns:
        if table_index >= 0:
            grouped.setdefault(table_index, []).append(str(column_name))
    return "; ".join(
        f"{table}({', '.join(grouped.get(index, []))})"
        for index, table in enumerate(tables)
    )


def sql_complexity(sql: str) -> str:
    normalized = " " + re.sub(r"\s+", " ", sql.upper()).strip() + " "
    nested = len(re.findall(r"\bSELECT\b", normalized)) > 1 or any(
        token in normalized for token in (" UNION ", " INTERSECT ", " EXCEPT ")
    )
    advanced = any(
        token in normalized
        for token in (" JOIN ", " GROUP BY ", " HAVING ", " ORDER BY ")
    )
    if nested:
        return "nested"
    if advanced:
        return "advanced"
    return "simple"


def convert_record(
    record: dict[str, Any], index: int, schemas: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    db_id = str(record["db_id"])
    if db_id not in schemas:
        raise ValueError(f"Missing schema for Spider database: {db_id}")
    question = str(record["question"]).strip()
    sql = str(record["query"]).strip()
    prompt = (
        "translate English to SQL: "
        f"question: {question} schema: {render_schema(schemas[db_id])}"
    )
    return {
        "dataset": "spider",
        "id": f"spider_{index:06d}_{db_id}",
        "db_id": db_id,
        "question": question,
        "input_text": prompt,
        "target_sql": sql,
        "complexity": sql_complexity(sql),
    }


def convert_records(
    records: Iterable[dict[str, Any]],
    schemas: dict[str, dict[str, Any]],
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    rows = list(records)
    if max_records is not None:
        rows = rows[:max_records]
    return [convert_record(row, index, schemas) for index, row in enumerate(rows)]


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--tables-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-records", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = convert_records(
        read_json(args.input), load_schemas(args.tables_json), args.max_records
    )
    write_jsonl(rows, args.output)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["complexity"]] = counts.get(row["complexity"], 0) + 1
    print(f"Converted {len(rows)} Spider examples -> {args.output}")
    print(f"Complexity counts: {counts}")


if __name__ == "__main__":
    main()
