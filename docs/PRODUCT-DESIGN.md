# Product Design Document — Job-Chatbot

## Implementation Variant

This repo is the **Anthropic SDK multi-agent** implementation. A hand-rolled orchestrator delegates to four specialist sub-agents (CompanyConfirm, Scraper, DB, Tester), each with its own system prompt and tool set. Demonstrates the multi-agent pattern using only the raw `anthropic` Python SDK — no orchestration framework.

## Design principles

1. **Plain language over jargon.** A user typing `find AI jobs at PwC` should not need to know what a Workday tenant is. We translate; we do not lecture.
2. **One question, one answer.** Every query produces exactly one summary block. We do not chain follow-up questions in this version. Ambiguity resolves to a clear error, not an interrogation.
3. **Deterministic output formats.** Same inputs, same CSV columns, same SQLite schema, same exit codes. Surprises in output are bugs.
4. **Fail loud and clear.** Errors include what we tried, what went wrong, and what the user can do next. No silent partial successes.
5. **Local-first.** The user's data never leaves their disk. We call out to the LLM provider for parsing; everything else is local I/O.
6. **Respect the user's terminal.** No taking over the screen. No animations that block the buffer. Rich is used for color and tables; it falls back to plain text when piped.
7. **Predictable performance.** A query takes seconds, not minutes. If it will be slow, we say so up front.

## User journeys

### Journey A: First-time install and first query

1. User clones the repo and runs `uv sync` from the project root.
2. User copies `.env.example` to `.env` and pastes their `ANTHROPIC_API_KEY`.
3. User runs `uv run job-chatbot` and sees a greeting plus the eight supported companies.
4. User types `find AI jobs at PwC in Bangalore` and presses Enter.
5. Progress lines appear: `Resolving PwC...`, `Fetching listings...`, `Saving 14 jobs...`, `Validating...`.
6. A summary block prints: `Found 14 jobs at PwC matching "AI" in "Bangalore". Saved to output/pwc_2026-05-26_193045.csv and output/jobs.db.`
7. User opens the CSV in their preferred tool and is happy.

### Journey B: Repeat user, third week in a row

1. User runs `uv run job-chatbot` from terminal muscle memory.
2. User types `find ML jobs at NVIDIA` (no location filter this week).
3. Tool reuses cached company resolution, prints progress, returns 47 listings.
4. User notices the CSV filename is timestamped, so it does not overwrite last week's.
5. User asks the next query in the same session: `find data engineer jobs at Salesforce in Hyderabad`. No restart needed.
6. User types `quit` and exits.

### Journey C: Power user piping CSV into another script

1. User schedules a daily cron job: `0 6 * * * cd /home/user/jobs && uv run job-chatbot --query "find SRE jobs at Cisco" >> log.txt 2>&1`.
2. Tool runs non-interactively, writes the CSV with its timestamped name, prints summary to stdout, exits 0.
3. User's follow-up script reads the newest `cisco_*.csv` from `output/`, normalizes it, and pushes to a private Postgres warehouse.
4. On a network failure the tool exits 2; cron mails the user the captured stderr.
5. User reads the error message, knows it was a transient network issue, and goes back to bed.

## Information architecture

| Tier | Document | Audience | When they hit it |
|---|---|---|---|
| 1 | `README.md` | Anyone | First click from GitHub. Decides whether to try the tool at all. |
| 2 | `docs/USER-MANUAL.md` | End users | After installing, when they want a recipe for a specific task. |
| 3 | `docs/PRD.md`, `docs/PRODUCT-DESIGN.md`, `docs/SYSTEM-DESIGN.md` | Product managers, designers, engineers | When deciding to contribute, fork, or build something similar. |
| 4 | `docs/UAT-PLAN.md`, `docs/TESTING.md` | QA, contributors writing tests | Right before they run or extend the test suite. |

The principle: the further from the top tier a reader goes, the more they have already committed to the project. Tier 1 is a five-second pitch; tier 4 assumes you have the repo cloned.

## Interaction patterns

### CLI prompt anatomy

The prompt is `job-chatbot> ` followed by a single-line input. Multi-line input is supported by pasting a block that ends in a newline; we treat any pasted block as one logical query. The user can interrupt an in-flight query with **Ctrl-C** — we abort the current API call, print `Cancelled.`, and return to the prompt. The user can quit the REPL with **Ctrl-D**, `quit`, or `exit` (case-insensitive). No `:wq`. No `bye`.

### Query grammar (informal)

```
find <keyword> jobs at <company> [in <location>]
```

Accepted variants include `show me <keyword> jobs at <company>`, `look for <keyword> at <company> in <location>`, and `search <company> for <keyword>`. The keyword can be multi-word (`machine learning`, `data engineer`). The location is optional and matches against the listing's `locationsText` field with substring match. Quotes are tolerated but not required.

### Output cadence

Progress lines appear one at a time as each step starts, so the user always knows what is happening. The summary prints at the end as a single block. File paths are printed verbatim and absolutely, so the user can copy-paste them into their file manager or another shell.

## Conversation design

### Greeting copy

```
Welcome to job-chatbot. I can search openings at PwC, JPMorgan Chase,
Salesforce, Cisco, Adobe, NVIDIA, Netflix, and Workday.

Try: find AI jobs at PwC in Bangalore
Type 'quit' to exit.
```

### Standard error messages

| Trigger | Message |
|---|---|
| Unknown company | `Sorry, I do not know "<name>". I currently support: PwC, JPMorgan Chase, Salesforce, Cisco, Adobe, NVIDIA, Netflix, Workday.` |
| Missing API key | `ANTHROPIC_API_KEY is not set. Add it to your .env file or export it in your shell, then try again.` |
| Network failure | `Could not reach <host>. Check your internet connection and try again. (details: <short error>)` |
| Empty result | `No jobs matched "<keyword>" at <company>` (with `" in <location>"` if location filter was used). `Nothing was saved.` |
| Validation failure | `The data came back, but it failed validation: <reason>. The CSV was saved to <path> for inspection, but nothing was written to the database.` |
| Workday 4xx/5xx | `<company>'s careers site returned <status>. This usually clears up in a few minutes. Try again later.` |
| Rate limit | `We are being rate-limited by <provider>. Waiting 30 seconds, then retrying.` |

### Tone guidelines

Use first person sparingly. `I found 12 jobs` is fine; `I am excited to help you today!` is not. Use the second person to direct the user (`Type 'quit' to exit`). Be specific in error messages: name the company, name the host, name the file. Avoid exclamation marks. Avoid emoji. Avoid the word "just" (`just try again` is dismissive). Avoid the word "simply." When in doubt, drop the adverb.

## Output format design

### CSV columns

| Column | Type | Rationale |
|---|---|---|
| `company` | text | The canonical company name as the user knows it (e.g. `PwC`, not `pricewaterhousecoopers`). Lets the user join across multiple CSVs by company. |
| `job_id` | text | Stable identifier from Workday. Forms half of our uniqueness key. |
| `title` | text | The role title as displayed on the careers site. No normalization; preserves the company's own phrasing. |
| `location` | text | The full `locationsText` string. May contain multiple cities; we do not split. |
| `posted_on` | date (ISO) | When Workday reports the role was posted. Useful for filtering stale listings downstream. |
| `url` | text | Deep link to the listing. The single most-clicked column. |
| `fetched_at` | timestamp (ISO, UTC) | When we ran this query. Lets the user reason about freshness. |

### SQLite schema

```sql
CREATE TABLE IF NOT EXISTS jobs (
    company     TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT,
    posted_on   TEXT,
    url         TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (company, job_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_fetched_at ON jobs (fetched_at);
```

### Naming convention for output files

CSVs are written to `output/<company>_<YYYY-MM-DD_HHMMSS>.csv` where `<company>` is the lowercased canonical name with spaces collapsed to underscores. The database is always `output/jobs.db`. We never overwrite a CSV. The directory `output/` is created on first run if absent.

## Accessibility

Terminal output works without colors: Rich is configured to autodetect TTY support and falls back to plain text when piped to a file or another process. Tables include header rows; data rows are never the first row. Progress is communicated via complete English sentences, not spinner characters that screen readers may pronounce as gibberish. The CSV is UTF-8 with `\n` line endings, readable by any standards-compliant CSV reader regardless of locale.

## Internationalization

Today, every user-facing string is English. Inputs are parsed by the LLM, so users can ask their query in any language the model handles, but progress and error messages always come back in English. Proper i18n would require: a string-extraction layer for our error templates, locale-aware date formatting for `posted_on`, awareness of Indian English city aliases (`Bengaluru` vs `Bangalore`), and validation on RTL terminals where progress bars currently right-justify oddly. None of this is in v0.1.

## Tone of voice and copy guidelines

Use verbs over nouns: `Saved 14 jobs` beats `Save count: 14`. Use active voice: `We could not reach the server` beats `The server could not be reached`. Be specific over generic: `output/pwc_2026-05-26_193045.csv` beats `your CSV file`. Avoid jargon at first mention: `Workday (the software hosting the careers site)` is fine the first time the term appears in a user-facing message; thereafter just `Workday`. Never apologize twice for the same thing in one message.

## Future UX explorations

### Streamlit web UI

A single-page Streamlit app reusing the same core orchestrator. Input box at the top, a results table in the middle, download buttons at the bottom. Hosted on Streamlit Community Cloud. The main UX challenge is conveying the same progress cadence the CLI has without forcing the user to stare at a spinner.

### Slack `/findjobs` bot

A Slack slash command that accepts the same NL query syntax and posts a threaded summary back to the channel. Useful for recruiting teams who already live in Slack. The challenge is permission scoping and rate limiting per workspace.

### Voice via Whisper plus Claude

A voice-activated mode that transcribes a spoken query via Whisper, parses with Claude, and reads the summary aloud. Niche, but plausible for users with accessibility needs. Latency budget is tight; voice users have far less patience than CLI users.

### Email digest

Weekly digest emails, opt-in, summarizing new listings since the previous digest. The main design question is what counts as "new": never-seen-before `job_id`, or anything updated this week.

### Browser extension

A browser extension that, when the user lands on a supported company's careers page, surfaces our cached listings as a sidebar. Helps users notice listings the on-site filter buried. Heavy maintenance burden; deferred indefinitely.

### Mobile read-only viewer

A static HTML viewer for the SQLite database, hosted from the user's own machine via a tiny web server, optimized for mobile screens. Lets the user browse last night's saved data on the train. Useful but not urgent.

## Brand and visual style

The product is text-only today. There is no logo, no color palette, no brand wordmark. Rich-rendered tables use Rich's default theme; we recommend `cyan` for headers and `green` for success summaries on the rare occasion we add explicit colors. Markdown documentation uses default typography — no custom CSS, no embedded fonts. If a logo emerges, it should be flat, monochrome, and legible at 16 pixels (favicon size).

## Open design questions

- Should REPL history persist on disk across sessions? Where do we store it, and how does the user clear it? `~/.job-chatbot/history` is the obvious answer but introduces a new directory we have to document.
- Do we offer query suggestions after a failed parse? `Did you mean: find <keyword> jobs at <company>?` would help new users but risks feeling preachy on repeated failures.
- How do we surface a `--watch` mode in v0.3 without breaking the "one query, one answer" principle? An always-running background process feels at odds with a CLI tool.
- Should we offer Parquet or JSON Lines exports alongside CSV? The data-eng persona wants Parquet; the recruiter persona wants Excel-friendly CSV. Both can be true.
- Do we expose the raw LLM tool-use trace to users for debugging? It is valuable for power users but noisy for everyone else. A `--verbose` flag is the obvious compromise.

## References

- `docs/PRD.md` — product requirements and success metrics.
- `docs/USER-MANUAL.md` — task-oriented walkthroughs.
- `docs/SYSTEM-DESIGN.md` — implementation architecture.
- `docs/UAT-PLAN.md` — user-acceptance test scenarios.
- `docs/TESTING.md` — automated test inventory.
