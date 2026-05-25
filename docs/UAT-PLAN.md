# User Acceptance Testing (UAT) Plan

This document is for a product manager, QA reviewer, or any non-engineer
verifying that `job-chatbot-anthropic-sdk` behaves correctly from a real
user's seat. Follow it top to bottom: prerequisites, setup, acceptance
scenarios, negative tests, sign-off.

---

## 1. What UAT covers

UAT is an **end-to-end** check of the chatbot from the user-facing REPL
(`job-chatbot-anthropic-sdk`). For every scenario you type a natural-language
prompt and observe the four-stage pipeline panel and the artifacts it writes
to `output/`.

UAT is deliberately distinct from the developer **unit smoke suite** in
`tests/test_smoke.py`. That suite is offline, fast, never calls the
Anthropic API, and is documented in `docs/TESTING.md`. UAT, by contrast,
runs the real `claude-haiku-4-5-20251001` model and the live Workday public
search API, so results may vary slightly day to day as job postings rotate.

This is the **anthropic-sdk** implementation. It runs four specialist
sub-agents — **CompanyConfirm**, **Scraper**, **DB**, **Tester** — each in
its own Anthropic SDK tool-use loop with its own system prompt and tool
set. UAT scenarios verify each sub-agent fires and the overall pipeline
hangs together.

What UAT does **not** cover:

- Code-level correctness of the storage helpers (covered by the unit smoke
  suite).
- Anthropic API outages, billing limits, or model deprecation (those are
  upstream concerns).
- Workday endpoint changes by individual companies.

---

## 2. Prerequisites

| Item | Minimum |
|------|---------|
| Operating system | macOS, Linux, or Windows (WSL / Git Bash) |
| Python | 3.11 or newer |
| `uv` | Latest — install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Anthropic API key | A working key from <https://console.anthropic.com> with budget remaining |
| Internet | Open access to `api.anthropic.com` and `*.myworkdayjobs.com` |
| Disk | A few MB for CSVs and a small SQLite DB in `output/` |

---

## 3. Setup checklist

Tick each box before running scenarios:

- [ ] Cloned the repo:
      `git clone git@github.com:mahadevaiahrashmi/job-chatbot-anthropic-sdk.git`
- [ ] Changed into the directory:
      `cd job-chatbot-anthropic-sdk`
- [ ] Installed dependencies:
      `uv sync`
- [ ] Copied the env template and pasted your key:
      `cp .env.example .env` and edit `.env` so `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Verified the smoke suite passes:
      `uv run pytest -q` — should report all passing in well under 5 seconds.
- [ ] Started the REPL:
      `uv run job-chatbot-anthropic-sdk`
- [ ] Observed the banner panel and a `you>` prompt.

If any of the above fails, stop and file a bug before proceeding.

---

## 4. Acceptance test scenarios

Each scenario is **independent** — quit and restart the REPL between
scenarios if you want a clean slate, otherwise it is acceptable to run them
in the same session. Pipeline output appears in a panel titled `pipeline`
and shows one line per sub-agent.

| ID | Title | User input (typed at `you>`) | Expected outcome |
|----|-------|------------------------------|------------------|
| **UAT-001** | Happy path: PwC + AI | `find AI jobs at PwC in Bangalore` | `Overall: PASS`. All four agents `ok`. ≥1 posting written. CSV path ends in `_ai_<date>.csv`. |
| **UAT-002** | Alias resolves: SFDC → Salesforce | `get data engineer openings from SFDC` | CompanyConfirm resolves to `Salesforce`. Pipeline passes. CSV file name slug begins with `salesforce_`. |
| **UAT-003** | Unknown company, graceful failure | `find product manager jobs at Acme Robotics` | `Overall: FAIL`. CompanyConfirm fails with a clear message naming the supported registry. **Scraper, DB, Tester do not appear in the panel** (pipeline short-circuits). |
| **UAT-004** | Empty result: NVIDIA + COBOL | `find COBOL roles at NVIDIA` | Pipeline ends with `Overall: FAIL` at the Scraper stage because zero postings come back. DB and Tester do not run. |
| **UAT-005** | ML keywords at Adobe | `find machine learning jobs at Adobe` | `Overall: PASS`. ≥1 posting. CSV slug includes `machine_learning`. |
| **UAT-006** | Location filter honored | `find software engineer jobs at Cisco in Bengaluru` | Every row in the produced CSV mentions Bengaluru (or Bangalore) in its `location` column. |
| **UAT-007** | No location given | `get all data scientist jobs at Workday` | CompanyConfirm normalizes with empty `location`. CSV contains postings from multiple cities. |
| **UAT-008** | Idempotent re-run | Run UAT-001 twice in the same REPL session, exactly the same prompt. | Both runs pass. The SQLite DB row count for `PricewaterhouseCoopers` does not double — upsert keeps it stable. A second timestamped CSV may appear; that is acceptable. |
| **UAT-009** | Excel-readable CSV | Open the CSV from UAT-001 in Excel / Numbers / LibreOffice. | Six columns: `company, job_id, title, location, posted_on, url`. No mojibake, no broken rows, links are clickable. |
| **UAT-010** | Cost sanity | After UAT-001, glance at the Anthropic console usage page. | Total cost for one happy-path run is small (≈ a few cents). If a single run costs more than a quarter, file a bug. |
| **UAT-011** | Per-agent observability | Run UAT-001. Read the `pipeline` panel carefully. | The panel lists **exactly four** sub-agent rows in order: `[company_confirm] ok`, `[scraper] ok`, `[db] ok`, `[tester] ok`. Each has a 1-line summary. This proves all four agents fired. |
| **UAT-012** | Sub-agent isolation on early failure | Run UAT-003 (unknown company). | Only `[company_confirm]` appears in the panel, and it is marked `FAIL`. `[scraper]`, `[db]`, and `[tester]` are absent because the orchestrator returns early. This proves sub-agents are isolated and do not fire if upstream fails. |

### How to record results

For each scenario record: ID, pass / fail, time taken (eyeball it), and any
deviations from the expected outcome. Attach a copy of the CSV from UAT-001
to the sign-off email.

---

## 5. Negative tests

These verify the chatbot **fails loudly and cleanly** when its environment
is wrong. Run them in addition to the table above.

| ID | Setup | Expected |
|----|-------|----------|
| **NEG-001** | Unset the key: `unset ANTHROPIC_API_KEY` (or empty `.env`). Run the REPL. | Banner prints, then a red message: *"ANTHROPIC_API_KEY is not set."* and the process exits with status 1. No crash, no traceback. |
| **NEG-002** | Disconnect from the internet. Run UAT-001. | CompanyConfirm may complete (no network needed for the registry tool) but Scraper fails when `httpx` cannot reach `myworkdayjobs.com`. The REPL prints `Pipeline error: ...` and returns to the `you>` prompt — it does **not** crash out of the REPL. |
| **NEG-003** | Delete `.env` entirely. | Same as NEG-001 — the env loader silently no-ops and the missing-key check trips. |
| **NEG-004** | At the `you>` prompt, press Enter on an empty line. | The REPL ignores the empty line and re-prompts. No pipeline runs. |
| **NEG-005** | Type `companies` at the `you>` prompt. | The REPL prints a comma-separated list of the eight supported canonical names and re-prompts. |
| **NEG-006** | Type `quit` (also `exit`, `:q`). | The REPL exits cleanly with status 0. |

---

## 6. Performance expectations

Because each of the four sub-agents runs its **own** Anthropic tool-use
loop (sometimes multiple round-trips per agent — see the loop in
`agents/company_confirm.py` which bounds at 6 turns, and `agents/tester.py`
which bounds at 8), end-to-end wall-clock time is dominated by Claude
latency, not by Workday or local I/O.

Use these honest thresholds during sign-off:

| Scenario | Expected wall-clock |
|----------|---------------------|
| Happy path (UAT-001, UAT-005, UAT-006) | **15–40 seconds** |
| Empty result (UAT-004) | 10–25 seconds (Tester does not run) |
| Unknown company (UAT-003) | 5–15 seconds (only CompanyConfirm runs) |
| Idempotent re-run (UAT-008) | Same as happy path each time |

If a happy-path run consistently exceeds **60 seconds**, file a performance
bug. Slowness is most often caused by Workday rate-limiting or a Claude
retry storm; both should be visible to the developer in logs.

---

## 7. Sign-off template

Copy / paste this block into the sign-off email or ticket once UAT is
complete:

```
UAT Sign-off — job-chatbot-anthropic-sdk
Build / commit:   <git short SHA>
Tester:           <name>
Date:             <YYYY-MM-DD>
Environment:      <OS, Python version, uv version>

Scenario results:
  UAT-001  [ pass / fail ]   notes:
  UAT-002  [ pass / fail ]   notes:
  UAT-003  [ pass / fail ]   notes:
  UAT-004  [ pass / fail ]   notes:
  UAT-005  [ pass / fail ]   notes:
  UAT-006  [ pass / fail ]   notes:
  UAT-007  [ pass / fail ]   notes:
  UAT-008  [ pass / fail ]   notes:
  UAT-009  [ pass / fail ]   notes:
  UAT-010  [ pass / fail ]   notes:
  UAT-011  [ pass / fail ]   notes:
  UAT-012  [ pass / fail ]   notes:

Negative tests:
  NEG-001  [ pass / fail ]
  NEG-002  [ pass / fail ]
  NEG-003  [ pass / fail ]
  NEG-004  [ pass / fail ]
  NEG-005  [ pass / fail ]
  NEG-006  [ pass / fail ]

Overall verdict:  [ APPROVED / APPROVED-WITH-NOTES / REJECTED ]
Attachments:      <CSV from UAT-001, screenshot of pipeline panel>
```

---

## 8. Reporting bugs

When a scenario fails, open an issue on the repo with:

1. **Scenario ID** (e.g. `UAT-004`) and a one-line title.
2. **What you typed** at the `you>` prompt, verbatim.
3. **Full pipeline panel output** — copy the panel from the terminal,
   including the `Overall:` line and every `[<agent>]` line. This is the
   most important diagnostic: it tells the developer which sub-agent
   tripped.
4. **Artifacts**: the path to any CSV in `output/`, and whether `jobs.db`
   exists.
5. **Environment**: OS, Python version (`python --version`), uv version
   (`uv --version`), git commit (`git rev-parse --short HEAD`).
6. **Time of day** and an estimate of wall-clock duration — useful for
   debugging upstream Anthropic or Workday slowness.

Do **not** paste your `ANTHROPIC_API_KEY` into a bug report.
