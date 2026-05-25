"""Scraper sub-agent.

Given a resolved :class:`JobQuery`, asks Claude to call the `search_workday`
tool with the right arguments. The tool is a thin wrapper around
``tools.workday.search_jobs`` so the real network call happens in Python.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from ..models import AgentResult, JobPosting, JobQuery
from ..tools.companies import resolve_company
from ..tools.workday import search_jobs

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the Scraper agent.

You receive a normalized JobQuery (company canonical name, keywords, optional
location, limit). Your single responsibility is to call the `search_workday`
tool with the right arguments, then call `report_results` summarizing how many
postings came back.

Rules:
- Pass the canonical company name unchanged into `search_workday`. The tool
  will resolve it to a Workday tenant internally.
- Do not invent additional keyword filters; pass exactly what you were given.
- After `search_workday` returns, call `report_results` exactly once.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_workday",
        "description": (
            "Query the Workday careers API for a company. Returns a list of "
            "job postings (company, job_id, title, location, posted_on, url)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Canonical company name from the registry.",
                },
                "keywords": {"type": "string"},
                "location": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["company"],
        },
    },
    {
        "name": "report_results",
        "description": "Report final counts and any notes. Call exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["count"],
        },
    },
]


def _tool_search_workday(
    company: str,
    keywords: str,
    location: str | None,
    limit: int,
    sink: list[JobPosting],
) -> dict[str, Any]:
    resolved = resolve_company(company)
    if resolved is None:
        return {"error": f"unknown company '{company}'"}
    postings = search_jobs(
        resolved,
        keywords=keywords or "",
        location=location,
        limit=limit,
    )
    sink.extend(postings)
    return {
        "count": len(postings),
        "sample": [p.to_dict() for p in postings[:3]],
    }


def run(query: JobQuery, client: anthropic.Anthropic) -> AgentResult:
    """Run the Scraper agent for the given normalized query."""
    user_msg = (
        "Scrape Workday for this query: "
        f"company='{query.company}', keywords='{query.keywords}', "
        f"location='{query.location or ''}', limit={query.limit}."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]
    postings: list[JobPosting] = []
    report: dict[str, Any] | None = None

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
            if block.name == "search_workday":
                result = _tool_search_workday(
                    block.input.get("company", query.company),
                    block.input.get("keywords", query.keywords) or "",
                    block.input.get("location") or query.location,
                    int(block.input.get("limit") or query.limit),
                    postings,
                )
            elif block.name == "report_results":
                report = dict(block.input)
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

        if report is not None:
            break

    ok = bool(postings)
    summary = (
        f"Scraped {len(postings)} postings from {query.company}."
        if ok
        else f"No postings returned for {query.company} with keywords '{query.keywords}'."
    )
    return AgentResult(
        agent="scraper",
        ok=ok,
        summary=summary,
        data={
            "postings": [p.to_dict() for p in postings],
            "report": report or {"count": len(postings)},
        },
    )
