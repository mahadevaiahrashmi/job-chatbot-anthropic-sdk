"""Smoke tests.

These do NOT call the Anthropic API. They verify:
  * every module imports cleanly
  * the Workday job-ID regex extracts the canonical ID
  * the company registry resolves common aliases
  * the storage helpers round-trip a posting through CSV + SQLite
"""

from __future__ import annotations

from pathlib import Path

import job_chatbot_anthropic_sdk
from job_chatbot_anthropic_sdk import models, orchestrator
from job_chatbot_anthropic_sdk.agents import company_confirm, db, scraper, tester
from job_chatbot_anthropic_sdk.tools import companies, storage, workday
from job_chatbot_anthropic_sdk.tools.workday import _extract_job_id


def test_modules_import():
    # If any of these imports failed, pytest would have errored at collection time.
    assert job_chatbot_anthropic_sdk.__version__
    assert models and orchestrator
    assert company_confirm and scraper and db and tester
    assert companies and storage and workday


def test_extract_job_id_with_suffix():
    assert (
        _extract_job_id(
            "/Global_Experienced_Careers/job/Bengaluru-Millenia/IN-Senior-Manager_712616WD-2"
        )
        == "712616WD"
    )


def test_extract_job_id_without_suffix():
    assert (
        _extract_job_id(
            "/Global_Experienced_Careers/job/Mumbai/Director-Cloud-Architecture_712616WD"
        )
        == "712616WD"
    )


def test_extract_job_id_fallback_for_unparseable():
    # No trailing WD ID -> fall back to the last path component.
    assert _extract_job_id("/jobs/legacy-role") == "legacy-role"
    assert _extract_job_id("") == ""


def test_resolve_company_canonical_and_alias():
    pwc = companies.resolve_company("pwc")
    assert pwc is not None
    assert pwc.canonical_name == "PricewaterhouseCoopers"
    assert pwc.tenant == "pwc"
    assert pwc.site == "Global_Experienced_Careers"

    assert companies.resolve_company("JP Morgan").canonical_name == "JPMorgan Chase"
    assert companies.resolve_company("SFDC").canonical_name == "Salesforce"
    assert companies.resolve_company("never-heard-of-them") is None


def test_known_companies_count():
    # Brief sanity check that all 8 registry entries are present.
    assert len(companies.known_companies()) == 8


def test_storage_round_trip(tmp_path: Path):
    postings = [
        models.JobPosting(
            company="PricewaterhouseCoopers",
            job_id="712616WD",
            title="AI Engineer",
            location="Bengaluru",
            posted_on="2026-05-20",
            url="https://example.com/job/712616WD",
        ),
        models.JobPosting(
            company="PricewaterhouseCoopers",
            job_id="712617WD",
            title="ML Engineer",
            location="Mumbai",
            posted_on="2026-05-21",
            url="https://example.com/job/712617WD",
        ),
    ]

    csv_path = storage.write_csv(postings, "pwc", "ai", output_dir=tmp_path)
    db_path = storage.write_sqlite(postings, "pwc", output_dir=tmp_path)

    assert csv_path.exists()
    assert db_path.exists()
    assert storage.csv_columns(csv_path) == storage.EXPECTED_CSV_COLUMNS
    assert storage.count_csv_rows(csv_path) == 2
    assert storage.csv_duplicate_job_ids(csv_path) == []
    assert storage.sqlite_row_count(db_path, "PricewaterhouseCoopers") == 2
