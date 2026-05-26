# Documentation index

> **Implementation variant:** Anthropic SDK — 4 hand-rolled sub-agents, no orchestration framework.

A guide to the documentation in this repository. Six core documents, organized by audience.

## Quick navigation

| Document | Audience | When to read |
|---|---|---|
| [USER-MANUAL.md](USER-MANUAL.md) | Non-technical users | First-time setup, daily usage, troubleshooting |
| [PRD.md](PRD.md) | Product managers, leads | Understanding what we're building and why |
| [PRODUCT-DESIGN.md](PRODUCT-DESIGN.md) | Designers, product engineers | UX patterns, copy, output formats |
| [SYSTEM-DESIGN.md](SYSTEM-DESIGN.md) | Engineers | Architecture, components, data flow |
| [UAT-PLAN.md](UAT-PLAN.md) | QA, product, anyone signing off | End-to-end acceptance verification |
| [TESTING.md](TESTING.md) | Engineers maintaining the project | Test strategy, mocking, adding tests |

## Which doc do I need?

```mermaid
flowchart TD
    Start{Why are you here?}
    Start -->|I want to use the tool| UM[USER-MANUAL.md]
    Start -->|I'm deciding whether to invest| PRD[PRD.md]
    Start -->|I'm designing UX or copy| PD[PRODUCT-DESIGN.md]
    Start -->|I'm reading or extending the code| SD[SYSTEM-DESIGN.md]
    Start -->|I'm verifying it works end-to-end| UAT[UAT-PLAN.md]
    Start -->|I'm writing or running tests| T[TESTING.md]
```

## Reading order by role

### First-time visitor
1. [README at repo root](../README.md) — what this is
2. [USER-MANUAL.md](USER-MANUAL.md) — install and use
3. [PRD.md](PRD.md) — only if you want product context

### Product manager
1. [PRD.md](PRD.md) — vision, goals, KPIs, roadmap
2. [PRODUCT-DESIGN.md](PRODUCT-DESIGN.md) — UX principles, future explorations
3. [UAT-PLAN.md](UAT-PLAN.md) — what's verifiable today

### Engineer joining the project
1. [README](../README.md) — quick start
2. [SYSTEM-DESIGN.md](SYSTEM-DESIGN.md) — architecture
3. [TESTING.md](TESTING.md) — how to add tests
4. [PRD.md](PRD.md) — context on the "why"

### Designer
1. [PRODUCT-DESIGN.md](PRODUCT-DESIGN.md) — principles, IA, copy
2. [USER-MANUAL.md](USER-MANUAL.md) — observe today's actual interactions
3. [PRD.md](PRD.md) — open design questions live here

### QA / acceptance testing
1. [USER-MANUAL.md](USER-MANUAL.md) — what users expect
2. [UAT-PLAN.md](UAT-PLAN.md) — scenarios + sign-off template
3. [TESTING.md](TESTING.md) — what's automated vs manual

## Audience × document matrix

|                 | Non-tech | Product | Design | Engineering | QA |
|-----------------|:---:|:---:|:---:|:---:|:---:|
| USER-MANUAL     | ●●● | ●   | ●   | ○   | ●● |
| PRD             | ○   | ●●● | ●●  | ●   | ●  |
| PRODUCT-DESIGN  | ○   | ●●  | ●●● | ●   | ●  |
| SYSTEM-DESIGN   |     | ●   | ○   | ●●● | ●  |
| UAT-PLAN        | ●●  | ●●  | ●   | ●   | ●●●|
| TESTING         |     |     |     | ●●● | ●  |

●●● primary · ●● useful · ● skim · ○ optional · (blank) skip

## Conventions across all six docs

- Markdown with `##` and `###` section headings
- Code fences include a language tag (` ```python `, ` ```bash `, ` ```sql `)
- Mermaid diagrams inside ` ```mermaid ` fences
- Tables for personas, scenarios, schemas, KPIs
- Verbatim user-facing copy is in double quotes
- Internal links are relative (e.g. `[USER-MANUAL.md](USER-MANUAL.md)`)

## See also

- [Repo README](../README.md) — high-level project overview
- [GitHub Issues](../../../issues) — open work items
- [Project board](https://github.com/users/mahadevaiahrashmi/projects/8) — roadmap and triage
- [Sibling implementations](https://github.com/mahadevaiahrashmi?tab=repositories&q=job-chatbot) — the other 4 variants of this product
