"""Workday careers API client.

Workday exposes an unauthenticated JSON search endpoint at:
  POST {base_url}/wday/cxs/{tenant}/{site}/jobs

with body shape:
  {
    "appliedFacets": {},
    "limit": 20,
    "offset": 0,
    "searchText": "<keywords>"
  }

The response includes a `jobPostings` array. We paginate until exhaustion
or until `limit` results have been collected.
"""

from __future__ import annotations

import re

import httpx

from ..models import JobPosting
from .companies import Company

_PAGE_SIZE = 20
_USER_AGENT = (
    "job-chatbot-anthropic-sdk/0.1 "
    "(+https://github.com/mahadevaiahrashmi/job-chatbot-anthropic-sdk)"
)
_JOB_ID_RE = re.compile(r"_([A-Z0-9-]+WD)(?:-\d+)?$")


def _extract_job_id(external_path: str) -> str:
    """Pull the canonical job ID (e.g. 712616WD) out of the externalPath.

    Workday externalPath looks like:
      /Global_Experienced_Careers/job/Bengaluru-Millenia/IN-Senior-..._712616WD
    or sometimes with a -1/-2 suffix. We strip the suffix so the same role
    surfaced on two careers sites still deduplicates.
    """
    match = _JOB_ID_RE.search(external_path or "")
    if match:
        return match.group(1)
    # Fall back to the full path if we can't parse a clean ID.
    return external_path.rsplit("/", 1)[-1] if external_path else ""


def search_jobs(
    company: Company,
    keywords: str = "",
    location: str | None = None,
    limit: int = 100,
) -> list[JobPosting]:
    """Search a Workday tenant for postings matching `keywords` and `location`."""
    endpoint = f"{company.base_url}/wday/cxs/{company.tenant}/{company.site}/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }

    results: list[JobPosting] = []
    seen_ids: set[str] = set()
    offset = 0

    with httpx.Client(timeout=20.0) as client:
        while len(results) < limit:
            body = {
                "appliedFacets": {},
                "limit": _PAGE_SIZE,
                "offset": offset,
                "searchText": keywords or "",
            }
            response = client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break

            for raw in postings:
                external_path = raw.get("externalPath", "")
                job_id = _extract_job_id(external_path)
                if not job_id or job_id in seen_ids:
                    continue
                posting_location = raw.get("locationsText", "") or ""
                if location and location.lower() not in posting_location.lower():
                    continue
                seen_ids.add(job_id)
                results.append(
                    JobPosting(
                        company=company.canonical_name,
                        job_id=job_id,
                        title=raw.get("title", ""),
                        location=posting_location,
                        posted_on=raw.get("postedOn", ""),
                        url=f"{company.base_url}{external_path}",
                    )
                )
                if len(results) >= limit:
                    break

            offset += _PAGE_SIZE
            total = data.get("total", offset)
            if offset >= total:
                break

    return results
