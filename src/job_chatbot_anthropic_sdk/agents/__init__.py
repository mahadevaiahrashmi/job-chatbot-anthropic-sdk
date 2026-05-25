"""Specialist sub-agents used by the orchestrator.

Each module exposes a `run(...)` function returning an
:class:`job_chatbot_anthropic_sdk.models.AgentResult`. The sub-agents are
intentionally narrow: each owns one phase of the pipeline (confirm, scrape,
persist, validate) and uses its own `anthropic.Anthropic` tool-use loop.
"""

from . import company_confirm, db, scraper, tester

__all__ = ["company_confirm", "scraper", "db", "tester"]
