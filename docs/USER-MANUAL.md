# User Manual

A friendly, step-by-step guide to running `job-chatbot-anthropic-sdk` on your
own machine. No Python knowledge required — if you can copy and paste a
shell command, you can use this tool.

---

## What this tool does

Type a request in plain English — for example, *"find AI jobs at PwC in
Bangalore"* — and the bot turns it into a real search against PwC's careers
website. It quietly fetches **every** matching job posting, saves them as a
spreadsheet (CSV file) and a small database (SQLite file) on your computer,
and tells you how many jobs it found.

Under the hood, four small AI "agents" cooperate: one figures out which
company you meant, one downloads the job postings, one writes the files, and
one double-checks the results. You never have to think about the agents
themselves — you just type a question and read the answer. The result is a
CSV you can open in Excel, Numbers, or Google Sheets, plus a database file
that accumulates every job you've ever searched for so you can query across
companies later.

---

## What you need before starting

- A computer running **macOS, Linux, or Windows** (with WSL or Git Bash on
  Windows).
- **Python 3.11 or newer.** Check with `python3 --version`. If you don't have
  it, grab it from [python.org/downloads](https://www.python.org/downloads/).
- An **Anthropic API key**. Sign up at
  [console.anthropic.com](https://console.anthropic.com), create a key under
  *API Keys*, and copy the value (it starts with `sk-ant-`).
- **`uv`** — a fast Python project manager. Install it with one line:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  (Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`)

That's it. No databases to set up, no servers to configure.

---

## Installing for the first time

Open a terminal and run these commands one at a time:

```bash
# 1. Clone the repository
git clone git@github.com:mahadevaiahrashmi/job-chatbot-anthropic-sdk.git

# 2. Move into the project folder
cd job-chatbot-anthropic-sdk

# 3. Create an isolated Python environment
uv venv

# 4. Install all dependencies
uv sync

# 5. Copy the example environment file
cp .env.example .env
```

Now open the `.env` file in any text editor (TextEdit, Notepad, VS Code…) and
replace the placeholder with your real Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-paste-your-real-key-here
```

Save and close the file. You're done installing.

---

## Running the bot

From the project folder, run:

```bash
uv run job-chatbot-anthropic-sdk
```

You'll see a welcome banner and a prompt that looks like this:

```
you>
```

That's where you type your question. The bot waits there until you press
Enter. Each line you type kicks off a full search — usually 5–20 seconds of
work — and prints a summary panel when it's done.

There are two special commands:

- Type **`companies`** to see the full list of companies the bot knows about.
- Type **`quit`** (or `exit`, or press Ctrl+D) to leave.

---

## Example queries

Here are eight queries you can try right away. After each, the bot creates a
CSV file inside the `output/` folder and appends the same rows to
`output/jobs.db`.

| You type | What the bot does |
|---|---|
| `find AI jobs at PwC in Bangalore` | Searches PwC's Workday site for "AI", keeps only postings whose location mentions Bangalore. Saves `output/pricewaterhousecoopers_ai_<date>.csv`. |
| `Find data scientist jobs at NVIDIA` | Searches NVIDIA worldwide for "data scientist". Saves `output/nvidia_data_scientist_<date>.csv`. |
| `List all PwC AI roles in Bangalore` | Same as the first query — the bot is forgiving about phrasing. |
| `get data engineer openings from Salesforce` | Searches Salesforce's careers site for "data engineer". |
| `show me all machine learning jobs at Adobe` | Searches Adobe for "machine learning". Often returns 50–100 results. |
| `Cisco openings in San Jose` | No keyword filter — returns every Cisco posting whose location mentions San Jose. |
| `JPMorgan Chase software engineer roles` | The bot recognises "JPMorgan Chase", "JP Morgan", "JPMC", and "Chase" as the same company. |
| `Netflix engineering jobs` | Returns Netflix engineering postings worldwide. |

When a query succeeds you'll see something like:

```
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

Each of the four lines (`company_confirm`, `scraper`, `db`, `tester`) is one
of the cooperating AI agents reporting its result.

---

## Where the results live

Every artifact ends up in the `output/` folder next to where you ran the
command:

- **`output/<company>_<keyword>_<date>.csv`** — one CSV per query.
  Example: `output/nvidia_data_scientist_2026-05-25.csv`.
  Open it in Excel, Numbers, Google Sheets, or any text editor.

- **`output/jobs.db`** — a single SQLite database that accumulates every
  posting you've ever fetched across every company. You can browse it with
  free tools like [DB Browser for SQLite](https://sqlitebrowser.org/) or
  query it from the command line with `sqlite3 output/jobs.db`.

The database is **idempotent**: running the same query twice doesn't create
duplicates. If a posting changes (new title, new location), the database row
is updated in place.

---

## Reading the CSV

Every CSV has the same six columns, in this order:

| Column | What it means |
|---|---|
| **company** | The canonical company name (e.g. `PricewaterhouseCoopers`, not `pwc`). |
| **job_id** | The unique ID assigned by the careers site, e.g. `712616WD`. Use this when applying or following up. |
| **title** | The job title as posted, e.g. `Senior Manager - AI/ML`. |
| **location** | The free-text location string from the careers site, e.g. `Bengaluru, Karnataka, India`. |
| **posted_on** | When the listing went live, in the careers site's own format. |
| **url** | A direct link to the posting. Click it to apply or read the full description. |

The bot guarantees no two rows in the same CSV share a `job_id` — duplicates
are filtered out during scraping.

---

## Supported companies

The bot currently knows about these eight Workday-hosted careers sites:

- Adobe
- Cisco
- JPMorgan Chase
- Netflix
- NVIDIA
- PricewaterhouseCoopers
- Salesforce
- Workday

You don't have to type the canonical name. Common aliases work too:

- `pwc`, `pricewaterhousecoopers`, `pwc india` all resolve to PwC.
- `jp morgan`, `jpmc`, `chase`, `jpmorgan chase` all resolve to JPMorgan Chase.
- `sfdc` resolves to Salesforce.

If the bot can't recognise the company you typed, it'll tell you and list the
supported ones.

---

## Common questions / troubleshooting

**Q: Why is it asking me for an Anthropic key?**
The four agents are powered by Claude (Anthropic's AI model), so the bot
needs to authenticate to Anthropic's API. Make sure your `.env` file contains
`ANTHROPIC_API_KEY=sk-ant-...` with a valid key, and that you're running the
command from the project folder (so `.env` is in the current directory).

**Q: Why is no CSV being created?**
A few things to check, in order:
1. Look at the pipeline panel. If a stage says `FAIL`, the message tells you
   which step bailed out (e.g. "Could not resolve the company").
2. If the scraper says `0 postings`, your keyword + location combination
   probably has zero matches on the careers site. Try a broader query.
3. If you see a network error, the careers site may be temporarily down. Try
   again in a minute.
4. Confirm the `output/` folder exists (the bot creates it automatically but
   restrictive permissions can block this).

**Q: What if my company isn't listed?**
Right now the bot only supports the eight companies above. Adding a new one
is a one-line change in `src/job_chatbot_anthropic_sdk/tools/companies.py` —
see `docs/SYSTEM-DESIGN.md` for instructions. If you don't write code, file
an issue on the repo with the company name and the URL of their careers
site.

**Q: How do I stop it?**
Type `quit` and press Enter, or press **Ctrl+C** / **Ctrl+D** at the prompt.

**Q: How fresh is the data?**
Every query hits the company's live careers site in real time — there's no
caching on the bot's side. What you see is what the company is showing on
its public careers page at that moment.

**Q: Can I run it without internet?**
No. The bot needs to talk to both the Anthropic API (for the AI agents) and
the company's careers website (to fetch postings).

**Q: Does it remember previous searches?**
Yes — `output/jobs.db` accumulates every posting you've ever fetched. Each
CSV, on the other hand, is specific to one query and is named with the date
it was created.

---

## Privacy & cost

**Cost.** Each query makes a handful of small calls to the Anthropic API —
one per agent stage. With Claude Haiku (the model this bot uses) a typical
end-to-end query costs a fraction of a US cent. You can check exact usage
under *Usage* on console.anthropic.com.

**Privacy.** Job listings are downloaded from public careers sites to your
local machine. Nothing about you (your name, your CV, your search history)
is sent anywhere — the bot doesn't have or need any personal information.
The only data the bot sends to Anthropic is the literal text of your query
plus the tool-call responses Claude needs to do its job; no scraped postings
ever leave your computer except by your own choice.
