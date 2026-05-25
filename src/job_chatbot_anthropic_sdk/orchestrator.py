"""Top-level orchestrator.

Drives a four-stage pipeline by delegating to specialist sub-agents:

    user_message
        -> CompanyConfirm   (Claude + resolve_company tool)
        -> Scraper          (Claude + search_workday tool)
        -> DB               (Claude + csv_write + sqlite_write tools)
        -> Tester           (Claude + four validation tools)
        -> summary string

Each sub-agent is its own ``anthropic.Anthropic.messages.create`` call with
its own system prompt and narrow tool set. The orchestrator only forwards
data between phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic

from .agents import company_confirm, db, scraper, tester
from .models import AgentResult, JobPosting, JobQuery


@dataclass
class PipelineResult:
    ok: bool
    summary: str
    stages: list[AgentResult]
    artifacts: dict[str, str]

    def render(self) -> str:
        lines = [f"Overall: {'PASS' if self.ok else 'FAIL'} - {self.summary}", ""]
        for s in self.stages:
            lines.append(f"  [{s.agent}] {'ok' if s.ok else 'FAIL'} - {s.summary}")
        if self.artifacts:
            lines.append("")
            lines.append("Artifacts:")
            for k, v in self.artifacts.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


def run_pipeline(
    user_message: str,
    client: anthropic.Anthropic | None = None,
    output_dir: Path = Path("output"),
) -> PipelineResult:
    """Run the full four-agent pipeline against ``user_message``."""
    client = client or anthropic.Anthropic()
    stages: list[AgentResult] = []
    artifacts: dict[str, str] = {}

    # 1. CompanyConfirm
    confirm = company_confirm.run(user_message, client)
    stages.append(confirm)
    if not confirm.ok:
        return PipelineResult(False, confirm.summary, stages, artifacts)

    q = confirm.data["query"]
    query = JobQuery(
        company=q["company"],
        keywords=q.get("keywords", ""),
        location=q.get("location"),
        limit=int(q.get("limit", 100)),
    )

    # 2. Scraper
    scrape = scraper.run(query, client)
    stages.append(scrape)
    if not scrape.ok:
        return PipelineResult(False, scrape.summary, stages, artifacts)

    postings = [
        JobPosting(**row) for row in scrape.data.get("postings", [])
    ]

    # 3. DB
    persist = db.run(query, postings, client, output_dir=output_dir)
    stages.append(persist)
    paths = persist.data.get("paths", {})
    artifacts.update(paths)
    if not persist.ok:
        return PipelineResult(False, persist.summary, stages, artifacts)

    # 4. Tester
    verify = tester.run(
        query,
        csv_path=paths.get("csv_path", ""),
        db_path=paths.get("db_path", ""),
        client=client,
    )
    stages.append(verify)

    ok = all(s.ok for s in stages)
    summary = (
        f"Pipeline complete: {len(postings)} postings for {query.company}."
        if ok
        else verify.summary
    )
    return PipelineResult(ok=ok, summary=summary, stages=stages, artifacts=artifacts)


__all__ = ["PipelineResult", "run_pipeline"]
