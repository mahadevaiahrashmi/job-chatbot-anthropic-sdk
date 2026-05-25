"""Tester sub-agent.

Validates the artifacts the DB agent wrote. Checks performed:
  * CSV exists, has the expected header columns.
  * CSV row count > 0.
  * CSV has no duplicate `job_id` values.
  * SQLite row count for the company > 0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic

from ..models import AgentResult, JobQuery
from ..tools.storage import (
    EXPECTED_CSV_COLUMNS,
    count_csv_rows,
    csv_columns,
    csv_duplicate_job_ids,
    sqlite_row_count,
)

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the Tester agent.

You receive paths to a CSV and a SQLite database. Run the four validation
tools below in any order, then call `report_verdict` summarizing pass/fail.

A run only passes if:
- `check_csv_schema` reports `ok=true`.
- `check_csv_rows` reports `count > 0`.
- `check_csv_dedup` reports `duplicates=[]`.
- `check_sqlite_rows` reports `count > 0`.

Call `report_verdict` exactly once at the end.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "check_csv_schema",
        "description": "Verify the CSV header matches the expected schema.",
        "input_schema": {
            "type": "object",
            "properties": {"csv_path": {"type": "string"}},
            "required": ["csv_path"],
        },
    },
    {
        "name": "check_csv_rows",
        "description": "Count data rows in the CSV (header excluded).",
        "input_schema": {
            "type": "object",
            "properties": {"csv_path": {"type": "string"}},
            "required": ["csv_path"],
        },
    },
    {
        "name": "check_csv_dedup",
        "description": "List any job_id values that appear more than once.",
        "input_schema": {
            "type": "object",
            "properties": {"csv_path": {"type": "string"}},
            "required": ["csv_path"],
        },
    },
    {
        "name": "check_sqlite_rows",
        "description": "Count postings in SQLite, optionally filtered by company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string"},
                "company": {"type": "string"},
            },
            "required": ["db_path"],
        },
    },
    {
        "name": "report_verdict",
        "description": "Report overall pass/fail. Call exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "notes": {"type": "string"},
            },
            "required": ["passed"],
        },
    },
]


def _tool_check_csv_schema(csv_path: str) -> dict[str, Any]:
    cols = csv_columns(Path(csv_path))
    return {
        "ok": cols == EXPECTED_CSV_COLUMNS,
        "actual": cols,
        "expected": EXPECTED_CSV_COLUMNS,
    }


def _tool_check_csv_rows(csv_path: str) -> dict[str, Any]:
    return {"count": count_csv_rows(Path(csv_path))}


def _tool_check_csv_dedup(csv_path: str) -> dict[str, Any]:
    return {"duplicates": csv_duplicate_job_ids(Path(csv_path))}


def _tool_check_sqlite_rows(db_path: str, company: str | None) -> dict[str, Any]:
    return {"count": sqlite_row_count(Path(db_path), company)}


def run(
    query: JobQuery,
    csv_path: str,
    db_path: str,
    client: anthropic.Anthropic,
) -> AgentResult:
    """Run the Tester agent on the artifacts produced by the DB agent."""
    user_msg = (
        f"Validate these artifacts for company='{query.company}'. "
        f"CSV: {csv_path}. SQLite DB: {db_path}."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

    findings: dict[str, Any] = {}
    verdict: dict[str, Any] | None = None

    for _ in range(8):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "check_csv_schema":
                result = _tool_check_csv_schema(block.input.get("csv_path", csv_path))
                findings["schema"] = result
            elif block.name == "check_csv_rows":
                result = _tool_check_csv_rows(block.input.get("csv_path", csv_path))
                findings["rows"] = result
            elif block.name == "check_csv_dedup":
                result = _tool_check_csv_dedup(block.input.get("csv_path", csv_path))
                findings["dedup"] = result
            elif block.name == "check_sqlite_rows":
                result = _tool_check_sqlite_rows(
                    block.input.get("db_path", db_path),
                    block.input.get("company") or query.company,
                )
                findings["sqlite"] = result
            elif block.name == "report_verdict":
                verdict = dict(block.input)
                result = {"accepted": True}
            else:
                result = {"error": f"unknown tool {block.name}"}
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

        if verdict is not None:
            break

    passed = bool(verdict and verdict.get("passed"))
    summary = (
        "All validation checks passed."
        if passed
        else (verdict or {}).get("notes")
        or "Tester agent did not return a passing verdict."
    )
    return AgentResult(
        agent="tester",
        ok=passed,
        summary=summary,
        data={"findings": findings, "verdict": verdict or {}},
    )
