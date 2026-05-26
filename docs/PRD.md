# Product Requirements Document — Job-Chatbot

## Implementation Variant

This repo is the **Anthropic SDK multi-agent** implementation. A hand-rolled orchestrator delegates to four specialist sub-agents (CompanyConfirm, Scraper, DB, Tester), each with its own system prompt and tool set. Demonstrates the multi-agent pattern using only the raw `anthropic` Python SDK — no orchestration framework.

## TL;DR

A conversational command-line tool that turns natural-language queries like `find AI jobs at PwC in Bangalore` into clean, structured job listings pulled directly from company careers sites. It targets eight Workday-hosted enterprise employers, persists results locally to CSV and SQLite, and validates every run. It is the lightweight, programmable alternative to LinkedIn job alerts for technical users who want to own their data.

## Problem statement

Job seekers who target a short list of specific employers waste hours each week navigating between five and twenty separate careers websites. The pain has three layers:

- **Fragmentation.** Each company hosts its careers portal independently. Workday alone powers thousands of these sites, but every tenant exposes its own URL, branding, and filter UX.
- **Weak filtering.** The default Workday UI offers location and keyword filters that often miss synonyms (`ML` vs `machine learning`), do not combine cleanly, and reset on every page reload.
- **Aggregator gaps.** LinkedIn and Indeed promise to consolidate listings but miss internal-only postings, surface stale data days after takedown, and bury filtering behind a paywall or an aggressive recommendation feed.

The irony is that every Workday careers site is backed by a structured JSON endpoint (`/wday/cxs/{tenant}/{site}/jobs`). The data is already clean. Accessing it just requires technical knowledge that most users do not have and should not need.

## Vision & opportunity

A conversational CLI that accepts natural-language queries and returns clean structured data. Local-first: every result lives on the user's disk in formats they already know how to read. The roadmap extends from CLI to a thin web UI, to scheduled monitoring with diff notifications, to a public hosted version with quota limits.

The bigger vision is to become the lightweight, programmable alternative to LinkedIn job alerts for technical users. We win not on coverage breadth (LinkedIn always has more total listings) but on data quality, programmability, and trust. A user who exports our CSV into their own dashboard, then triggers it weekly from cron, is a user who never goes back.

## Target users (personas)

| Persona | Snapshot | Why they use it |
|---|---|---|
| Career-pivot Priya | Senior engineer, 8 years experience, evaluating opportunities across eight specific large employers. Spends Sunday evenings browsing. | Wants a single command that returns every fresh listing matching her interests, without logging into eight separate sites. |
| Recruiter Ramesh | Agency recruiter, runs weekly snapshots of competitor open roles to brief his enterprise clients. | Wants reproducible, timestamped snapshots so he can compute week-over-week deltas and spot hiring surges. |
| Data-eng Devika | Data engineer who runs a personal jobs dashboard in Metabase. | Wants a programmable feed she can schedule, pipe into her warehouse, and join against compensation data. |

## Goals

- **G1.** Resolve any of the eight supported company names (and common aliases) to a valid Workday tenant + site pair with 100 % accuracy.
- **G2.** Return all listings matching a keyword + location filter from a target company's Workday site, with no duplicates, in under 30 seconds at P95.
- **G3.** Persist every successful run to both CSV and SQLite, with upsert semantics so repeat runs do not duplicate rows.
- **G4.** Validate every output before declaring success, catching empty results, schema drift, and obvious garbage.
- **G5.** Keep average API cost per query under 10 US cents.
- **G6.** Ship a binary-free, install-in-one-command experience that runs on macOS, Linux, and Windows with Python 3.11 or newer.

## Non-goals

- **NG1.** We do not apply to jobs on the user's behalf. No form-filling, no resume submission.
- **NG2.** We do not store the user's resume, profile, or any personally identifiable information.
- **NG3.** We do not notify users of new postings in this version. Scheduled diffing is on the roadmap, not in v0.1.
- **NG4.** We do not scrape LinkedIn, Indeed, Glassdoor, or any aggregator. We pull from primary sources only.
- **NG5.** We do not compete on coverage breadth. Eight companies is the cap for v0.1, growing deliberately.
- **NG6.** We do not build a hiring-side product (ATS, recruiter CRM, candidate ranking). The user is always the job seeker or analyst.

## Functional requirements

- **FR-1.** Accept natural-language queries via a CLI REPL that survives across multiple queries in one session.
- **FR-2.** Parse queries of the form `find <keyword> jobs at <company> [in <location>]` plus common variants (`show me`, `look for`, `search`).
- **FR-3.** Resolve company names through an alias map: `pwc`, `pricewaterhousecoopers`, `pricewaterhouse coopers`, `pwc consulting` all map to the same tenant.
- **FR-4.** Implement a Workday API client that POSTs to `/wday/cxs/{tenant}/{site}/jobs` with proper pagination (`limit`, `offset`) and follows the documented response schema.
- **FR-5.** Apply keyword filtering case-insensitively across `title` and (where present) `bulletFields`. Apply location filtering against the `locationsText` field with substring match.
- **FR-6.** Export every successful run to a CSV file under `output/` named `<company>_<YYYY-MM-DD_HHMMSS>.csv`.
- **FR-7.** Upsert every row into a SQLite database at `output/jobs.db`, keyed on `(company, job_id)`, updating `fetched_at` and any changed fields on conflict.
- **FR-8.** Run a validation pass after every persistence step: row count > 0, required columns non-null, no obviously malformed URLs.
- **FR-9.** Handle network errors, 4xx and 5xx responses, and rate limits with a clear user-facing message and a non-zero exit code on hard failures.
- **FR-10.** Make all reruns idempotent: running the same query twice produces the same final SQLite state, modulo `fetched_at`.
- **FR-11.** Provide a REPL with input history, `quit`/`exit`/Ctrl-D shortcuts, and Ctrl-C cancellation of in-flight queries.
- **FR-12.** Run identically on macOS, Linux, and Windows. Output file paths must use `pathlib` and avoid OS-specific separators.

## Non-functional requirements

- **NFR-1.** P95 end-to-end latency under 30 seconds for a typical query returning fewer than 200 listings.
- **NFR-2.** Average LLM cost under 10 US cents per query at observed token usage.
- **NFR-3.** The offline unit-test suite (no network, no LLM) completes in under 2 seconds.
- **NFR-4.** Targets Python 3.11 and newer. No support for 3.10 or earlier.
- **NFR-5.** Cross-platform: macOS, Linux, Windows. CI runs on all three.
- **NFR-6.** Zero PII collected, logged, or persisted. Logs may contain query text but never user identity.
- **NFR-7.** All dependencies installed via `uv sync` from a checked-in lockfile. No `pip install` instructions in user docs.
- **NFR-8.** No external services required beyond the LLM provider API. No accounts, no databases, no message queues.

## User stories

- As **Career-pivot Priya**, I want to run `find machine learning jobs at NVIDIA in Bangalore` so that I see every matching listing without opening NVIDIA's careers site.
- As **Career-pivot Priya**, I want my previous CSV files preserved so that I can compare this week's listings against last week's manually.
- As **Recruiter Ramesh**, I want to run the same eight queries every Monday morning and produce eight timestamped CSVs so that I can attach them to my client briefings.
- As **Recruiter Ramesh**, I want the SQLite database to retain history so that I can compute week-over-week deltas with a SQL query.
- As **Data-eng Devika**, I want a stable CSV schema so that my downstream loader does not break when a new field appears.
- As **Data-eng Devika**, I want a non-zero exit code on failure so that my cron wrapper can alert me when something goes wrong.
- As any user, I want a friendly error message when I type a company name we do not support, listing the eight we do.
- As any user, I want the tool to tell me exactly where it saved my data so that I do not have to hunt for the file.

## Success metrics

| Funnel stage | Metric | Target (v0.1) | Target (v1.0) |
|---|---|---|---|
| Acquisition | GitHub stars | 100 | 2 000 |
| Acquisition | Monthly unique downloaders | 250 | 5 000 |
| Activation | % of installs that complete a first successful query | 70 % | 85 % |
| Engagement | Average queries per active session | 3 | 6 |
| Retention | D7 return rate | 25 % | 45 % |
| Retention | D30 return rate | 10 % | 25 % |
| Quality | % of runs ending in a validation pass | 95 % | 99 % |
| Cost | Average US cents per query | 8¢ | 4¢ |

## Constraints & dependencies

- **Workday API stability.** The `/wday/cxs/{tenant}/{site}/jobs` endpoint is not officially documented for public consumption. Workday could change the contract or rate-limit anonymous traffic at any time.
- **LLM provider availability and pricing.** The product depends on a hosted LLM for natural-language parsing. A provider outage halts the user-facing entry point; a price hike directly degrades NFR-2.
- **Eight hardcoded companies.** The v0.1 alias map and tenant table are static. Adding a ninth company requires a code change and release.
- **No Workday partnership.** We have no commercial relationship with Workday. Our access depends entirely on the public unauthenticated endpoint behavior.

## Risks & mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Workday changes the `/wday/cxs` JSON schema | Medium | High | Schema-validate every response; ship a hotfix release within 48 h; pin a known-good client version |
| R2 | LLM provider raises prices by 2x | Medium | Medium | Cache parsed query plans; add a non-LLM regex fallback for the canonical query shape |
| R3 | A target company migrates off Workday | Low | Medium | Detect 404 on the tenant URL; report clearly; queue an ATS-of-the-month replacement |
| R4 | Legal challenge over scraping | Low | High | Stay on the unauthenticated public endpoint; respect robots.txt; provide an easy opt-out mechanism if contacted |
| R5 | LLM hallucinates a company that does not exist | Medium | Low | Validate every resolved company against the alias map before any HTTP call; refuse unknown companies |

## Release plan

- **v0.1 (now).** CLI REPL, eight companies, CSV + SQLite, validation. Single supported LLM provider. macOS + Linux only on day one, Windows shortly after.
- **v0.2 (Q3).** Configurable company list via YAML. Better keyword synonyms. Improved error messages. Windows-tested in CI.
- **v0.3 (Q4).** Scheduled mode (`--watch`) that polls every N hours and writes a diff log. Optional Slack webhook for diff notifications.
- **v0.5 (Q1 next year).** Thin Streamlit web UI on top of the same core. Hosted demo at a public URL.
- **v0.8 (Q2 next year).** Second LLM provider supported. Per-query routing by cost.
- **v1.0 (one year from v0.1).** Stable schema, semantic-version commitment, full Windows support, 25 supported companies, optional hosted SaaS tier in private beta.

## Out of scope (this version)

- Email or push notifications when new listings appear.
- Applying to jobs or filling application forms.
- Resume parsing or match scoring.
- Salary inference or compensation analysis.
- Non-Workday ATSes (Greenhouse, Lever, SmartRecruiters, Taleo).
- Multi-user or multi-tenant deployment.
- A web UI of any kind.
- Mobile clients.

## Open questions

- Should we deduplicate identical roles posted in multiple cities into a single canonical row, or preserve each city as a separate row?
- Is there demand for a hosted SaaS version, and at what price point would it actually convert?
- Does a web UI come before or after scheduled monitoring? Which unlocks more retention?
- Should we support multiple LLM providers from day one, or commit to one provider and revisit at v0.5?
- What is the right pricing model if we host this? Per-query, per-month, per-company-watched?
- Should we extend beyond Workday to Greenhouse and Lever in v1.0, or stay focused and deepen Workday coverage?
- Do we expose the raw LLM tool-use trace to users for debugging, or hide it behind a `--verbose` flag?
- Should query history persist across REPL sessions on disk, and if so, where and how is it cleared?

## Glossary

- **ATS.** Applicant Tracking System. The vendor software a company uses to host its careers site and manage applications. Workday is one ATS; Greenhouse, Lever, and Taleo are others.
- **Workday tenant.** The subdomain identifier in a Workday careers URL, e.g. `pwc` in `pwc.wd3.myworkdayjobs.com`.
- **Workday site.** The career-site slug under a tenant, e.g. `Global_Experienced_Careers`. A tenant can host multiple sites.
- **JobPosting.** One row in our CSV / SQLite, representing a single advertised role at a single company at a single point in time.
- **Upsert.** Insert if absent, update if present. We use it to keep `(company, job_id)` unique while letting `fetched_at` and other mutable fields refresh.
- **REPL.** Read-Eval-Print Loop. The interactive prompt the user types queries into.
- **Validation pass.** A post-write check that confirms the run produced sensible data before reporting success to the user.

## References

- `docs/USER-MANUAL.md` — task-oriented walkthroughs for end users.
- `docs/SYSTEM-DESIGN.md` — implementation architecture for engineers.
- `docs/PRODUCT-DESIGN.md` — interaction, copy, and UX guidelines.
- `docs/UAT-PLAN.md` — user-acceptance test scenarios.
- `docs/TESTING.md` — automated test inventory and coverage targets.
- GitHub issue tracker — open bugs and feature requests.
- Project board — current sprint and roadmap visibility.
