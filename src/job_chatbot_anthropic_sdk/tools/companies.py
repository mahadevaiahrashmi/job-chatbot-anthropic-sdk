"""Registry of known companies and their Workday endpoints.

Each entry maps an alias (lowercase) to the Workday tenant and site name.
Add new companies here, or extend `resolve_company` to probe at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    canonical_name: str
    base_url: str
    tenant: str
    site: str


_REGISTRY: dict[str, Company] = {
    "pwc": Company(
        canonical_name="PricewaterhouseCoopers",
        base_url="https://pwc.wd3.myworkdayjobs.com",
        tenant="pwc",
        site="Global_Experienced_Careers",
    ),
    "jpmorgan": Company(
        canonical_name="JPMorgan Chase",
        base_url="https://jpmc.wd5.myworkdayjobs.com",
        tenant="jpmc",
        site="jpmc",
    ),
    "salesforce": Company(
        canonical_name="Salesforce",
        base_url="https://salesforce.wd12.myworkdayjobs.com",
        tenant="salesforce",
        site="External_Career_Site",
    ),
    "cisco": Company(
        canonical_name="Cisco",
        base_url="https://cisco.wd5.myworkdayjobs.com",
        tenant="cisco",
        site="External",
    ),
    "adobe": Company(
        canonical_name="Adobe",
        base_url="https://adobe.wd5.myworkdayjobs.com",
        tenant="adobe",
        site="external_experienced",
    ),
    "nvidia": Company(
        canonical_name="NVIDIA",
        base_url="https://nvidia.wd5.myworkdayjobs.com",
        tenant="nvidia",
        site="NVIDIAExternalCareerSite",
    ),
    "netflix": Company(
        canonical_name="Netflix",
        base_url="https://netflix.wd1.myworkdayjobs.com",
        tenant="netflix",
        site="Netflix",
    ),
    "workday": Company(
        canonical_name="Workday",
        base_url="https://workday.wd5.myworkdayjobs.com",
        tenant="workday",
        site="Workday",
    ),
}


_ALIASES: dict[str, str] = {
    "pricewaterhousecoopers": "pwc",
    "price waterhouse coopers": "pwc",
    "pwc india": "pwc",
    "jp morgan": "jpmorgan",
    "jpmorgan chase": "jpmorgan",
    "jpmc": "jpmorgan",
    "chase": "jpmorgan",
    "sfdc": "salesforce",
}


def resolve_company(name: str) -> Company | None:
    """Look up a company by name or alias. Case-insensitive, ignores extra spaces."""
    key = " ".join(name.lower().split())
    if key in _REGISTRY:
        return _REGISTRY[key]
    if key in _ALIASES:
        return _REGISTRY[_ALIASES[key]]
    return None


def known_companies() -> list[str]:
    """Sorted list of canonical company names for help text."""
    return sorted(c.canonical_name for c in _REGISTRY.values())


def all_keys() -> list[str]:
    """All registry keys for use in agent prompts."""
    return sorted(_REGISTRY.keys())
