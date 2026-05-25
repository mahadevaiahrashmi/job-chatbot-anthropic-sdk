# Testing Guide

This document is for developers extending `job-chatbot-anthropic-sdk`. It
describes what the current test suite covers, how to run it, how to add
new tests, and — most importantly for this architecture — how to add a new
sub-agent or a new tool while keeping the suite green.

End-user / QA acceptance testing lives in `docs/UAT-PLAN.md`. That is a
separate, online, end-to-end verification. This document is strictly about
the offline developer suite.

---

## 1. Testing philosophy

The chatbot has three external dependencies — the Anthropic API, the
Workday public search endpoint, and the local filesystem — and three
sub-agent LLM loops on top of them. Our developer suite is deliberately
narrow:

- **Offline.** No network calls. `httpx` is never invoked.
- **Fast.** The whole suite finishes in well under five seconds, so it can
  run on every save.
- **No Anthropic.** The four sub-agents (`agents/company_confirm.py`,
  `agents/scraper.py`, `agents/db.py`, `agents/tester.py`) each contain a
  Claude tool-use loop. Those loops are **not** exercised by tests. The
  Python tools they wrap (`tools/companies.py`, `tools/workday.py`,
  `tools/storage.py`) **are**, directly.
- **No mocks where a real call works.** CSV / SQLite tests use a real
  temp directory; the regex test uses a real string; the registry test
  uses the real in-process registry.

This means the developer suite gives high confidence in the **deterministic**
layer (parsing, persistence, registry lookups) and zero coverage of the
**LLM-driven** layer (which sub-agent calls which tool, in what order, with
what arguments). That is by design — LLM behaviour belongs in UAT, not in a
unit suite.

---

## 2. What's covered today

All current tests live in a single file: `tests/test_smoke.py`. Each
function below is taken verbatim from that file:

| Test function | What it asserts |
|---------------|-----------------|
| `test_modules_import` | Every public module imports cleanly: package `__version__`, `models`, `orchestrator`, all four agent modules (`company_confirm`, `scraper`, `db`, `tester`), and the three tool modules. Acts as a free smoke check for syntax / import errors in every file in the codebase. |
| `test_extract_job_id_with_suffix` | The regex in `tools/workday.py::_extract_job_id` strips the `-2` suffix from `..._712616WD-2` and returns the canonical `712616WD`. |
| `test_extract_job_id_without_suffix` | The same regex returns `712616WD` from a path ending in `..._712616WD` with no trailing suffix. |
| `test_extract_job_id_fallback_for_unparseable` | If the regex cannot find a `…_<ID>WD` pattern, the function falls back to the last path segment (`legacy-role` for `/jobs/legacy-role`) and returns an empty string for empty input. |
| `test_resolve_company_canonical_and_alias` | `companies.resolve_company` resolves `"pwc"` to the `PricewaterhouseCoopers` registry entry (canonical name, tenant `pwc`, site `Global_Experienced_Careers`), maps the aliases `"JP Morgan"` → `JPMorgan Chase` and `"SFDC"` → `Salesforce`, and returns `None` for an unknown name. |
| `test_known_companies_count` | The registry contains exactly 8 entries. Forces a deliberate decision when adding or removing companies. |
| `test_storage_round_trip` | End-to-end exercise of `tools/storage.py` against a `tmp_path`: write two postings to CSV, write them to SQLite, then re-open both and verify (a) files exist, (b) CSV headers match `EXPECTED_CSV_COLUMNS`, (c) CSV row count is 2, (d) no duplicate `job_id`s, (e) SQLite row count filtered by company is 2. |

That is the entirety of the developer suite — seven tests, one file, all
deterministic.

---

## 3. Test categories

We do not split tests into directories yet. Conceptually:

**Unit tests** (the bulk of the suite):

- Regex behaviour for Workday job-ID extraction (`_extract_job_id`).
- Company registry lookups and alias handling.
- CSV / SQLite storage primitives in isolation.

**Integration tests**:

- `test_storage_round_trip` is a small integration test — it writes a CSV,
  writes a SQLite DB, and validates both with the same helpers the Tester
  sub-agent uses at runtime. That is the closest thing in the current
  suite to an integration test.

**Honest gaps** (no coverage today):

- The four sub-agent `run()` functions in `agents/`. None of them are
  unit-tested. The `_tool_*` dispatcher functions inside each agent are
  not directly invoked by tests either — they are reached only through a
  real Claude tool-use loop at runtime.
- The orchestrator's stage-by-stage flow in `orchestrator.py::run_pipeline`.
- The CLI entry point in `main.py` (the REPL loop, banner, `companies`
  command, exit codes).
- The live Workday HTTP client (`tools.workday.search_jobs`).

Filling those gaps requires either mocking the Anthropic client (out of
scope today) or moving the assertion to UAT (preferred).

---

## 4. How to run tests

```bash
# Run the whole suite, quiet output:
uv run pytest -q

# Verbose, with collected test IDs and durations:
uv run pytest -v --durations=10

# Filter by test name (substring match):
uv run pytest -k extract_job_id

# Filter by file:
uv run pytest tests/test_smoke.py

# Re-run only the tests that failed last time:
uv run pytest --lf

# Stop at the first failure:
uv run pytest -x
```

Tests do not require `ANTHROPIC_API_KEY` to be set, and do not consume API
credits. They are safe to run in CI without secrets.

---

## 5. Mocking strategy

Today the suite uses **no monkeypatching** — it does not need to. The
deliberate choice is:

- **Workday HTTP (`tools.workday.search_jobs`) is not called** by any test.
  If a future test exercises it, the recommended approach is to
  `monkeypatch` `httpx.Client.post` to return a canned JSON payload that
  mimics a real Workday response (an `appliedFacets` echo plus a
  `jobPostings` array). Do not record-and-replay actual HTTP traffic.
- **Anthropic `messages.create` is not called** by any test. Each
  sub-agent's tool-use loop is therefore not exercised. The Python
  dispatcher functions (`_tool_resolve_company`, `_tool_search_workday`,
  `_tool_csv_write`, `_tool_sqlite_write`, the four `_tool_check_*`
  functions in `tester.py`) **could** be unit-tested directly without any
  Anthropic mock — they are plain Python that takes a dict and returns a
  dict. That is the recommended path if you want to grow agent coverage
  without paying for tokens.

If you eventually need to mock the Anthropic client, prefer a thin fake
that returns a synthesized `Message` object whose `.content` is a list of
`tool_use` blocks. Do not pull in a heavyweight HTTP recorder; the SDK
already abstracts the transport.

---

## 6. Adding a new test

Worked example: suppose we add a new alias `"the firm"` → `Salesforce` in
`tools/companies.py`. Add a test that pins the new behaviour:

```python
def test_resolve_company_handles_new_alias():
    c = companies.resolve_company("the firm")
    assert c is not None
    assert c.canonical_name == "Salesforce"
```

Put it in `tests/test_smoke.py` alongside `test_resolve_company_canonical_and_alias`
unless and until that file grows past ~300 lines, at which point split it.

Conventions:

- One assertion per concept, but multiple `assert` statements per test
  are fine.
- Use `tmp_path` (pytest builtin) for any test that touches the
  filesystem. Never write to the real `output/` directory.
- Name tests `test_<unit>_<behaviour>`. Past tense reads worse — prefer
  `test_resolve_company_handles_alias` over `test_resolve_company_handled_alias`.
- Do not import `anthropic` from tests. If you find yourself wanting to,
  you are almost certainly about to mock something that should be UAT.

---

## 7. Adding a new sub-agent

This is the most architecturally interesting extension. The
**anthropic-sdk** implementation runs each agent as its own Anthropic
tool-use loop, so adding one is mechanical but touches several files.

### 7a. Skeleton

Create `src/job_chatbot_anthropic_sdk/agents/<name>.py`. Mirror the shape
of the existing agents (e.g. `agents/scraper.py`):

```python
MODEL = "claude-haiku-4-5-20251001"
SYSTEM_PROMPT = """You are the <Name> agent. ..."""
TOOLS: list[dict[str, Any]] = [
    {"name": "do_thing", "description": "...", "input_schema": {...}},
    {"name": "report_results", "description": "...", "input_schema": {...}},
]

def _tool_do_thing(...) -> dict[str, Any]:
    # plain Python that calls into tools/
    ...

def run(query: JobQuery, client: anthropic.Anthropic) -> AgentResult:
    messages = [{"role": "user", "content": "..."}]
    for _ in range(6):  # safety bound on the tool-use loop
        response = client.messages.create(
            model=MODEL, max_tokens=1024,
            system=SYSTEM_PROMPT, tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        # dispatch tool_use blocks, append tool_results, loop
```

Key invariants to preserve:

- **Bound the loop.** Every existing agent caps the tool-use loop (6 or 8
  iterations). Pick a finite number; never `while True`.
- **Return an `AgentResult`.** Use the dataclass in `models.py`:
  `agent="<name>"`, `ok=<bool>`, `summary=<one line>`, `data={...}`.
- **A `report_*` terminal tool.** Every existing agent has a final
  no-op-ish tool the LLM calls exactly once to signal completion
  (`submit_query`, `report_results`, `report_paths`, `report_verdict`).
  This is what tells the loop to break.

### 7b. Wire into the orchestrator

Edit `src/job_chatbot_anthropic_sdk/orchestrator.py`:

```python
from .agents import company_confirm, db, scraper, tester, <name>

# inside run_pipeline, between Scraper and DB (or wherever it fits):
new_stage = <name>.run(query, client)
stages.append(new_stage)
if not new_stage.ok:
    return PipelineResult(False, new_stage.summary, stages, artifacts)
```

### 7c. Re-export from the package

Edit `src/job_chatbot_anthropic_sdk/agents/__init__.py` to re-export the
new module so `from .agents import <name>` works.

### 7d. Tests

Crucially, the LLM loop in `run()` is **not** unit-tested. What you test
is:

- The new module imports cleanly — extend `test_modules_import` to import
  the new submodule.
- The Python `_tool_*` dispatchers — call them directly with sample input
  and assert their return shape.
- Any new helpers you added in `tools/`.

This matches what we do for every other agent today.

---

## 8. Adding a new tool to an existing agent

A tool is the pair of (a) a JSON schema entry in the agent's `TOOLS`
list and (b) a Python function that gets dispatched when the LLM calls
that name.

Steps, using `agents/scraper.py` as the example:

1. **Add a schema** to `TOOLS` in `agents/scraper.py`:

   ```python
   {
       "name": "filter_by_remote",
       "description": "Filter postings to remote-only roles.",
       "input_schema": {
           "type": "object",
           "properties": {"remote": {"type": "boolean"}},
           "required": ["remote"],
       },
   }
   ```

2. **Add a Python dispatcher** in the same file (or in `tools/` if it is
   reusable). Mirror the existing `_tool_search_workday` shape — take
   plain args, return a dict that will be JSON-serialized into the
   `tool_result`:

   ```python
   def _tool_filter_by_remote(postings: list[JobPosting], remote: bool) -> dict[str, Any]:
       filtered = [p for p in postings if ("remote" in p.location.lower()) == remote]
       return {"count": len(filtered)}
   ```

3. **Wire it into the dispatch chain** inside `run()`:

   ```python
   elif block.name == "filter_by_remote":
       result = _tool_filter_by_remote(postings, bool(block.input.get("remote")))
   ```

4. **Test the dispatcher directly** — do not test the LLM's choice to call
   it. Pass a synthetic posting list, assert the count.

5. **Update the agent's `SYSTEM_PROMPT`** if the new tool is mandatory or
   needs guidance.

---

## 9. Test data / fixtures

We do not have a `fixtures/` directory yet. Conventions:

- **In-memory data**: construct `JobPosting` and `JobQuery` objects inline
  in the test (see `test_storage_round_trip` for the pattern).
- **Filesystem**: use the pytest `tmp_path` fixture. Never write to
  `output/` from a test.
- **Workday payloads**: when you eventually need fake HTTP responses,
  store them as `.json` files under `tests/fixtures/workday/<company>.json`
  and load them with `json.loads(Path(...).read_text())`. Strip
  personal data and recruiter contact info before committing.

---

## 10. What's deliberately NOT tested

The omissions below are intentional. Resist the urge to fix them with
mocks unless you have a concrete reason.

- **Live tool-use loops.** Each of the four sub-agents (`company_confirm`,
  `scraper`, `db`, `tester`) runs a real Claude conversation at runtime.
  Stubbing the Anthropic client into a test gives you brittle assertions
  about exactly which tool the LLM chose to call first, which is exactly
  the wrong thing to pin down. UAT covers this end-to-end.
- **Workday HTTP.** `tools.workday.search_jobs` performs real network
  I/O. Mocking it would be straightforward but adds maintenance load
  (Workday's payload changes more often than ours).
- **Interactive REPL.** `main.py` reads from stdin and writes via
  `rich.Console`. A pty-based test is high-effort and low-value here.
- **Cost accounting.** We do not assert on token usage. UAT-010 in
  `docs/UAT-PLAN.md` covers cost sanity at the human-eyeball level.

---

## 11. Coverage

We do not currently measure coverage. Eyeballing
`tests/test_smoke.py` against the codebase: storage helpers are at ~95 %
line coverage, the registry is at 100 %, the Workday regex is at 100 %,
the four sub-agent modules are at ~10 % (only module-level import paths
hit), `main.py` and `orchestrator.py` are at ~0 %.

To wire coverage in:

```bash
uv add --dev pytest-cov
uv run pytest --cov=job_chatbot_anthropic_sdk --cov-report=term-missing
```

For CI it is reasonable to require coverage **only** on `tools/` (the
deterministic layer) — `agents/` and `main.py` will read as low forever
because the suite intentionally skips the LLM loops.

---

## 12. Continuous integration

CI is not wired up yet. A reasonable starting point is the workflow below.
It runs `pytest -q` on every push and pull request against `main`,
without requiring any secrets.

```yaml
# .github/workflows/ci.yml (not yet committed)
name: ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Sync deps
        run: uv sync
      - name: Run tests
        run: uv run pytest -q
```

Add a `lint` job once the linters in section 14 are configured.

---

## 13. Test smells

Heuristics for spotting tests that look fine today but will hurt later:

- **Asserting on which tool the LLM chose.** If a test imports `anthropic`
  and mocks `messages.create` to return a hard-coded tool-use block, it
  is testing the prompt, not the code. Move it to UAT.
- **Asserting on exact Workday response shape.** Workday changes its JSON
  fields periodically. Test the *output* of `search_jobs` (a list of
  `JobPosting`s) — not the *input* it consumed.
- **Tests that touch `output/`.** Always use `tmp_path`. A test that
  leaves files behind is leaking state.
- **Tests with sleeps.** None today. Keep it that way; the suite must
  stay sub-second per test.
- **Counting registry entries by literal.** `test_known_companies_count`
  asserts `len(...) == 8`. That is intentional — it forces a code review
  when the registry changes. Do not weaken it to `>= 1`.

---

## 14. Linting and type-checking

Neither `ruff` nor `mypy` is configured in `pyproject.toml` today. When
they are wired up, recommended baseline:

```toml
# pyproject.toml additions (not yet committed)
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src/job_chatbot_anthropic_sdk"]
```

Until then, rely on:

- `uv run pytest -q` (catches import-time errors via `test_modules_import`).
- A manual `python -c "import job_chatbot_anthropic_sdk"` before pushing.
- Editor / LSP type hints (every public function in the codebase already
  has annotations).

When you add `ruff` and `mypy`, add a `lint` job to the CI workflow in
section 12.
