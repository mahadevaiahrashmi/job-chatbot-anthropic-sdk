# job-chatbot-anthropic-sdk

Conversational, multi-agent job-search chatbot built with the
[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).
Type a query in plain English, get a clean CSV + SQLite snapshot of every
matching job posting on a Workday-hosted careers site.

---

## For Non-Technical Users

Tell the bot something like **"find AI jobs at PwC in Bangalore"** and a few
seconds later you'll have a spreadsheet on your computer listing every
matching job at PwC — title, location, posted date, and a direct link to
apply. Four small AI helpers cooperate behind the scenes: one figures out
which company you meant, one downloads the postings, one writes the file,
and one double-checks the result. You only ever type a question and read
the answer.

### Quick start in plain English

The friendly, step-by-step install + usage guide lives in
**[`docs/USER-MANUAL.md`](docs/USER-MANUAL.md)**. Start there if you don't
write code.

### What you'll need

- macOS, Linux, or Windows (WSL/Git Bash on Windows).
- Python 3.11 or newer.
- An Anthropic API key — sign up at [console.anthropic.com](https://console.anthropic.com).
- `uv` (one-line install: `curl -LsSf https://astral.sh/uv/install.sh | sh`).

### Supported companies

The registry currently covers eight Workday-hosted careers sites — Adobe,
Cisco, JPMorgan Chase, Netflix, NVIDIA, PricewaterhouseCoopers, Salesforce,
and Workday. Common aliases (`pwc`, `jp morgan`, `sfdc`, …) resolve
automatically.

### Example session

```
you> find AI jobs at PwC in Bangalore
+- pipeline ----------------------------------------------------------------+
| Overall: PASS - Pipeline complete: 17 postings for PricewaterhouseCoopers. |
|                                                                            |
|   [company_confirm] ok - Resolved company='PricewaterhouseCoopers', ...    |
|   [scraper] ok - Scraped 17 postings from PricewaterhouseCoopers.          |
|   [db] ok - Wrote 17 rows to CSV and SQLite.                               |
|   [tester] ok - All validation checks passed.                              |
|                                                                            |
| Artifacts:                                                                 |
|   csv_path: /.../output/pricewaterhousecoopers_ai_2026-05-25.csv           |
|   db_path:  /.../output/jobs.db                                            |
+----------------------------------------------------------------------------+
```

Type `companies` at the prompt to list supported companies, `quit` to exit.

---

## For Developers

### Architecture in one paragraph

A plain-Python orchestrator drives four narrow Claude sub-agents in
sequence: **CompanyConfirm** (resolve the user's company name to a
canonical registry entry) → **Scraper** (call the Workday public search
endpoint via a tool, paginate, filter by location) → **DB** (persist to a
timestamped CSV and upsert into `output/jobs.db`) → **Tester** (re-open
both artifacts and validate schema, row count, dedup, and SQLite count).
Each agent is its own `anthropic.Anthropic.messages.create` call with its
own system prompt and a tiny tool list — easier to reason about, debug,
and extend than one giant prompt.

### Tech stack

- **Anthropic Python SDK** (`anthropic>=0.40`) — agent calls, all using
  `claude-haiku-4-5-20251001`.
- **httpx** — Workday HTTP client.
- **rich** — REPL panels.
- **python-dotenv** — `.env` loading.
- **uv** — environment + dependency management.
- **pytest** — smoke tests (no network, no Anthropic calls).

### Code layout

```
job-chatbot-anthropic-sdk/
├── pyproject.toml
├── README.md
├── LICENSE
├── .env.example
├── docs/
│   ├── USER-MANUAL.md       # end-user walkthrough
│   └── SYSTEM-DESIGN.md     # architecture deep-dive
├── src/job_chatbot_anthropic_sdk/
│   ├── main.py              # CLI entry point
│   ├── orchestrator.py      # drives the four sub-agents (no LLM here)
│   ├── models.py            # JobQuery, JobPosting, AgentResult dataclasses
│   ├── agents/
│   │   ├── company_confirm.py
│   │   ├── scraper.py
│   │   ├── db.py
│   │   └── tester.py
│   └── tools/
│       ├── workday.py       # Workday search client + job-ID regex
│       ├── companies.py     # registry + alias map
│       └── storage.py       # CSV + SQLite writers
├── tests/test_smoke.py
└── output/                  # gitignored CSVs + jobs.db land here
```

### Dev quickstart

```bash
git clone git@github.com:mahadevaiahrashmi/job-chatbot-anthropic-sdk.git
cd job-chatbot-anthropic-sdk

uv venv
uv sync

cp .env.example .env
# paste your ANTHROPIC_API_KEY into .env

uv run job-chatbot-anthropic-sdk     # run the REPL
uv run pytest -q                     # run the smoke suite (no network)
```

The test suite does **not** call the Anthropic API. It exercises module
imports, the Workday job-ID regex, the company registry, and the CSV +
SQLite storage helpers end-to-end against a temp directory.

### Deeper dive

For the full architecture, agent-by-agent breakdown, the Anthropic tool-use
loop, the persistence schema, failure-mode matrix, and extension points,
see **[`docs/SYSTEM-DESIGN.md`](docs/SYSTEM-DESIGN.md)**.

---

## License

MIT — see [`LICENSE`](LICENSE).
