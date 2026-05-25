"""Data models for job postings and search queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobQuery:
    """A normalized job query produced by the CompanyConfirm agent."""

    company: str
    keywords: str
    location: str | None = None
    limit: int = 100


@dataclass
class JobPosting:
    """A single job posting scraped from a careers site."""

    company: str
    job_id: str
    title: str
    location: str
    posted_on: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "job_id": self.job_id,
            "title": self.title,
            "location": self.location,
            "posted_on": self.posted_on,
            "url": self.url,
        }


@dataclass
class AgentResult:
    """Generic result envelope returned by each sub-agent."""

    agent: str
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
