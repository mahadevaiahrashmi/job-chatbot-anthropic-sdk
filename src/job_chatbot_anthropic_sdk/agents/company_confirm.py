"""CompanyConfirm sub-agent.

Takes the user's raw chat message ("get all jobs from PwC related to AI in
Bangalore") and asks Claude — with a `resolve_company` tool — to normalize it
into a :class:`JobQuery` (company, keywords, location, limit).
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from ..models import AgentResult, JobQuery
from ..tools.companies import known_companies, resolve_company

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the CompanyConfirm agent.

Your job: read a user's free-form chat message asking for jobs at some company
and produce a normalized query. You MUST use the `resolve_company` tool to
verify the company is in the supported registry, then call `submit_query` with
the final structured result.

Rules:
- The `company` you submit must be the canonical name returned by
  `resolve_company` (e.g. "PricewaterhouseCoopers", not "pwc").
- If the company is not in the registry, call `submit_query` with company=""
  and an explanatory `notes` field.
- `keywords` should be the topical search terms (e.g. "AI", "machine learning",
  "data engineer"). Strip filler like "all jobs about" or "openings related to".
  If the user only names a company with no topic, use an empty string.
- `location` is optional. Extract it only if the user names a city or country.
- `limit` defaults to 100. Honor an explicit user limit if given.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "resolve_company",
        "description": (
            "Look up a company alias in the supported registry. Returns the "
            "canonical name and Workday endpoint, or null if unknown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Company name or alias as typed by the user.",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "submit_query",
        "description": (
            "Submit the final normalized JobQuery. Call exactly once at the end."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Canonical company name, or '' if unresolved.",
                },
                "keywords": {"type": "string"},
                "location": {"type": "string"},
                "limit": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["company", "keywords"],
        },
    },
]


def _tool_resolve_company(name: str) -> dict[str, Any]:
    c = resolve_company(name)
    if c is None:
        return {
            "resolved": False,
            "input": name,
            "supported_companies": known_companies(),
        }
    return {
        "resolved": True,
        "canonical_name": c.canonical_name,
        "tenant": c.tenant,
        "site": c.site,
        "base_url": c.base_url,
    }


def run(user_message: str, client: anthropic.Anthropic) -> AgentResult:
    """Run the CompanyConfirm agent on a user message."""
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_message},
    ]

    submitted: dict[str, Any] | None = None

    for _ in range(6):  # safety bound on the tool-use loop
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
            if block.name == "resolve_company":
                result = _tool_resolve_company(block.input.get("name", ""))
            elif block.name == "submit_query":
                submitted = dict(block.input)
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

        if submitted is not None:
            break

    if submitted is None or not submitted.get("company"):
        return AgentResult(
            agent="company_confirm",
            ok=False,
            summary=(submitted or {}).get("notes")
            or "Could not resolve the company to a supported entry.",
            data={"submitted": submitted or {}},
        )

    query = JobQuery(
        company=submitted["company"],
        keywords=submitted.get("keywords", "") or "",
        location=(submitted.get("location") or None) or None,
        limit=int(submitted.get("limit") or 100),
    )
    return AgentResult(
        agent="company_confirm",
        ok=True,
        summary=(
            f"Resolved company='{query.company}', keywords='{query.keywords}', "
            f"location='{query.location or ''}', limit={query.limit}."
        ),
        data={"query": query.__dict__},
    )
