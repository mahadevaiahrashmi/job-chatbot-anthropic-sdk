# job-chatbot-anthropic-sdk

Conversational chatbot that asks Claude to coordinate four specialist agents —
**CompanyConfirm**, **Scraper**, **DB**, **Tester** — to fetch and persist job
postings from Workday-hosted careers sites. Built with the
[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) using
its tool-use loop to delegate each stage of the pipeline to its own narrowly
scoped Claude call.

## How the agents fit together

```
                 +----------------------+
   user msg ---> |  Orchestrator        |
                 |  (Python, no LLM)    |
                 +----------+-----------+
                            |
              1. confirm    |
                            v
            +-------------------------+   tool: resolve_company
            |  CompanyConfirm agent   |   model: claude-haiku-4-5
            +-----------+-------------+
                        |  JobQuery
                        v
            +-------------------------+   tool: search_workday
            |  Scraper agent          |   model: claude-haiku-4-5
            +-----------+-------------+
                        |  list[JobPosting]
                        v
            +-------------------------+   tools: csv_write, sqlite_write
            |  DB agent               |   model: claude-haiku-4-5
            +-----------+-------------+
                        |  csv_path, db_path
                        v
            +-------------------------+   tools: check_csv_schema,
            |  Tester agent           |          check_csv_rows,
            +-----------+-------------+          check_csv_dedup,
                        |  pass/fail            check_sqlite_rows
                        v
                summary back to user
```

Each agent is its own `anthropic.Anthropic.messages.create` call with its own
system prompt and tool list. The orchestrator (`orchestrator.py`) is plain
Python — no LLM — so the multi-agent boundaries are explicit.

## Quickstart

```bash
git clone git@github.com:mahadevaiahrashmi/job-chatbot-anthropic-sdk.git
cd job-chatbot-anthropic-sdk

uv venv
uv sync

cp .env.example .env
# edit .env and paste your ANTHROPIC_API_KEY

uv run job-chatbot-anthropic-sdk
```

## Example session

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

## Supported companies

The registry currently covers eight Workday-hosted careers sites:

- Adobe
- Cisco
- JPMorgan Chase
- Netflix
- NVIDIA
- PricewaterhouseCoopers
- Salesforce
- Workday

Common aliases (`pwc`, `jp morgan`, `sfdc`, ...) resolve automatically; see
`src/job_chatbot_anthropic_sdk/tools/companies.py` to extend.

## Project layout

```
job-chatbot-anthropic-sdk/
├── pyproject.toml
├── README.md
├── LICENSE
├── .env.example
├── src/job_chatbot_anthropic_sdk/
│   ├── main.py              # CLI entry point
│   ├── orchestrator.py      # drives the four sub-agents
│   ├── models.py            # JobQuery, JobPosting, AgentResult
│   ├── agents/
│   │   ├── company_confirm.py
│   │   ├── scraper.py
│   │   ├── db.py
│   │   └── tester.py
│   └── tools/
│       ├── workday.py       # Workday search client
│       ├── companies.py     # registry + alias map
│       └── storage.py       # CSV + SQLite writers
├── tests/test_smoke.py
└── output/                  # gitignored CSVs and jobs.db land here
```

## Testing

```bash
uv run pytest -q
```

The test suite does **not** call the Anthropic API. It exercises module
imports, the Workday job-ID regex, the company registry, and the CSV +
SQLite storage helpers end-to-end against a temp directory.

## License

MIT — see `LICENSE`.
