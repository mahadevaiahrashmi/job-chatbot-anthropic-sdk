"""CLI entry point: ``job-chatbot-anthropic-sdk``.

Starts an interactive REPL. Each user prompt drives the full
CompanyConfirm -> Scraper -> DB -> Tester pipeline via the orchestrator.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from .orchestrator import run_pipeline
from .tools.companies import known_companies

BANNER = """[bold]job-chatbot-anthropic-sdk[/bold]
Multi-agent job-search chatbot (Anthropic Python SDK).

Type a request like:
  [italic]find AI jobs at PwC in Bangalore[/italic]
  [italic]get data engineer openings from Salesforce[/italic]

Type 'companies' to list supported companies, 'quit' to exit.
"""


def main() -> int:
    load_dotenv()
    console = Console()
    console.print(Panel.fit(BANNER))

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]ANTHROPIC_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key.[/red]"
        )
        return 1

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            user = console.input("[bold cyan]you>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0

        if not user:
            continue
        if user.lower() in {"quit", "exit", ":q"}:
            return 0
        if user.lower() == "companies":
            console.print("Supported: " + ", ".join(known_companies()))
            continue

        try:
            result = run_pipeline(user, output_dir=output_dir)
        except Exception as exc:  # pragma: no cover - defensive
            console.print(f"[red]Pipeline error: {exc}[/red]")
            continue

        console.print(Panel(result.render(), title="pipeline"))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
