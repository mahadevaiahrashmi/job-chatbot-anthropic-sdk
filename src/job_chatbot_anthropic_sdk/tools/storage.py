"""Persistence helpers: CSV writer + SQLite writer.

Both functions return the absolute filesystem path of the artifact they wrote
so downstream agents (Tester in particular) can re-open the file and validate.
"""

from __future__ import annotations

import csv
import datetime as _dt
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from ..models import JobPosting

_CSV_COLUMNS = ["company", "job_id", "title", "location", "posted_on", "url"]
_DEFAULT_OUTPUT_DIR = Path("output")


def _slug(text: str) -> str:
    """Lowercase, replace non-alphanumerics with underscores, collapse runs."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "unknown"


def _ensure_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_csv(
    postings: Iterable[JobPosting],
    company_slug: str,
    keyword_slug: str,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> Path:
    """Write postings to output_dir/{company}_{keyword}_{YYYY-MM-DD}.csv."""
    output_dir = _ensure_dir(output_dir)
    date = _dt.date.today().isoformat()
    filename = f"{_slug(company_slug)}_{_slug(keyword_slug)}_{date}.csv"
    path = output_dir / filename

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for p in postings:
            writer.writerow(p.to_dict())

    return path.resolve()


def write_sqlite(
    postings: Iterable[JobPosting],
    company_slug: str,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> Path:
    """Upsert postings into output_dir/jobs.db (table `postings`)."""
    output_dir = _ensure_dir(output_dir)
    db_path = output_dir / "jobs.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS postings (
                company TEXT NOT NULL,
                job_id TEXT NOT NULL,
                title TEXT,
                location TEXT,
                posted_on TEXT,
                url TEXT,
                inserted_at TEXT NOT NULL,
                PRIMARY KEY (company, job_id)
            )
            """
        )
        now = _dt.datetime.utcnow().isoformat(timespec="seconds")
        rows = [
            (
                p.company,
                p.job_id,
                p.title,
                p.location,
                p.posted_on,
                p.url,
                now,
            )
            for p in postings
        ]
        conn.executemany(
            """
            INSERT INTO postings(company, job_id, title, location, posted_on, url, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company, job_id) DO UPDATE SET
                title = excluded.title,
                location = excluded.location,
                posted_on = excluded.posted_on,
                url = excluded.url,
                inserted_at = excluded.inserted_at
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    return db_path.resolve()


def count_csv_rows(path: Path) -> int:
    """Count data rows (header excluded) in a CSV file."""
    with Path(path).open("r", encoding="utf-8") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def csv_columns(path: Path) -> list[str]:
    """Return the CSV header columns."""
    with Path(path).open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            return next(reader)
        except StopIteration:
            return []


def csv_duplicate_job_ids(path: Path) -> list[str]:
    """Return any job IDs that appear more than once in the CSV."""
    seen: dict[str, int] = {}
    with Path(path).open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            jid = row.get("job_id", "")
            if not jid:
                continue
            seen[jid] = seen.get(jid, 0) + 1
    return sorted(jid for jid, n in seen.items() if n > 1)


def sqlite_row_count(db_path: Path, company: str | None = None) -> int:
    """Count rows in the postings table, optionally filtered by company."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        if company:
            cur.execute(
                "SELECT COUNT(*) FROM postings WHERE company = ?", (company,)
            )
        else:
            cur.execute("SELECT COUNT(*) FROM postings")
        (count,) = cur.fetchone()
        return int(count)
    finally:
        conn.close()


EXPECTED_CSV_COLUMNS = _CSV_COLUMNS
