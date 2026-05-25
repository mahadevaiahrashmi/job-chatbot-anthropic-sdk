"""DB sub-agent.

Asks Claude to persist a list of postings via two tools: `csv_write` and
`sqlite_write`. Both wrap the helpers in ``tools.storage``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anthropic

from ..models import AgentResult, JobPosting, JobQuery
from ..tools.storage import write_csv, write_sqlite

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the DB agent.

You receive a JobQuery and a count of in-memory postings already collected by
the Scraper. Your job is to persist them to durable storage. You MUST:

1. Call `csv_write` once with the company and keywords. It writes a timestamped
   CSV to the output/ directory.
2. Call `sqlite_write` once with the same company. It upserts rows into a
   shared output/jobs.db SQLite database.
3. Call `report_paths` exactly once with both filesystem paths.

Do not invent or alter the posting list — the Python side already holds it.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "csv_write",
        "description": (
            "Write the in-memory postings to a timestamped CSV. Returns the "
            "absolute file path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_slug": {"type": "string"},
                "keyword_slug": {"type": "string"},
            },
            "required": ["company_slug", "keyword_slug"],
        },
    },
    {
        "name": "sqlite_write",
        "description": (
            "Upsert the in-memory postings into output/jobs.db. Returns the "
            "absolute database path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_slug": {"type": "string"},
            },
            "required": ["company_slug"],
        },
    },
    {
        "name": "report_paths",
        "description": "Report the CSV and DB paths. Call exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "csv_path": {"type": "string"},
                "db_path": {"type": "string"},
            },
            "required": ["csv_path", "db_path"],
        },
    },
]


def _tool_csv_write(
    postings: list[JobPosting],
    company_slug: str,
    keyword_slug: str,
    output_dir: Path,
) -> dict[str, Any]:
    path = write_csv(postings, company_slug, keyword_slug, output_dir=output_dir)
    return {"path": str(path), "rows": len(postings)}


def _tool_sqlite_write(
    postings: list[JobPosting],
    company_slug: str,
    output_dir: Path,
) -> dict[str, Any]:
    path = write_sqlite(postings, company_slug, output_dir=output_dir)
    return {"path": str(path), "rows": len(postings)}


def run(
    query: JobQuery,
    postings: list[JobPosting],
    client: anthropic.Anthropic,
    output_dir: Path = Path("output"),
) -> AgentResult:
    """Run the DB agent: persist postings to CSV + SQLite."""
    user_msg = (
        f"Persist {len(postings)} postings for company='{query.company}', "
        f"keywords='{query.keywords}'."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]
    paths: dict[str, str] = {}
    reported = False

    for _ in range(6):
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
            if block.name == "csv_write":
                result = _tool_csv_write(
                    postings,
                    block.input.get("company_slug", query.company),
                    block.input.get("keyword_slug", query.keywords or "all"),
                    output_dir,
                )
                paths["csv_path"] = result["path"]
            elif block.name == "sqlite_write":
                result = _tool_sqlite_write(
                    postings,
                    block.input.get("company_slug", query.company),
                    output_dir,
                )
                paths["db_path"] = result["path"]
            elif block.name == "report_paths":
                paths.setdefault("csv_path", block.input.get("csv_path", ""))
                paths.setdefault("db_path", block.input.get("db_path", ""))
                reported = True
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

        if reported and "csv_path" in paths and "db_path" in paths:
            break

    ok = "csv_path" in paths and "db_path" in paths
    summary = (
        f"Wrote {len(postings)} rows to CSV and SQLite."
        if ok
        else "DB agent failed to persist all artifacts."
    )
    return AgentResult(
        agent="db",
        ok=ok,
        summary=summary,
        data={"paths": paths, "row_count": len(postings)},
    )
