# Documentation

This folder documents **what made the project possible** — the infrastructure
and the process around the application itself. The app and the notebooks are
the deliverable; this is the story of how they were built and how the
inference stack behind them was set up.

## Contents

| Topic | What it covers |
|---|---|
| [`local-inference/SETUP.md`](local-inference/SETUP.md) | The self-hosted LLM endpoint: vLLM on a 2-GPU machine (systemd service, tuned serving flags, monitoring) and Ollama as the no-GPU alternative — plus how the app and notebooks wire into it |
| [`SETUP.md` § BYOK](local-inference/SETUP.md#bonus-developing-with-the-on-prem-agent-byok) | Proof: the entire repository was developed with an **on-prem coding agent** — VS Code wired via BYOK to the same self-hosted vLLM endpoint, no cloud LLM involved (screenshots in the guide) |
| [`adr/`](adr/README.md) | Architecture decision records — the key technical decisions (no framework at runtime, BM25 at runtime, 3-layer env, PII in pipeline, SQLite facts DB) with context and consequences |

## How this project was built

**Self-hosted, self-tuned, end to end.** Every LLM call that went into this
repository — the pipeline notebooks, the app development, the code review —
ran against the on-prem vLLM server described in
[`local-inference/SETUP.md`](local-inference/SETUP.md). No cloud API was used at
any point during development.

![The on-prem coding agent at work](local-inference/byok-vscode-2026-08-30_02-56-47.png)

<em>Figure 1: The on-prem coding agent at work — VS Code wired via BYOK to the self-hosted vLLM endpoint.</em>

The application (Streamlit app + pipeline notebooks) was written and
iterated on with a coding agent that talks to the local vLLM endpoint —
the same endpoint the finished app uses in production. And bringing up the
inference machine is a project in itself: the vLLM setup documented in
[`local-inference/SETUP.md`](local-inference/SETUP.md) is a reusable result on its
own — any similar RAG or agent workload on your own hardware can start from
that configuration.

## Outlook

The current system is a **stateless RAG pipeline**: one question in, one
cited answer out. The deliberate choice to keep the app framework-free
(see the main [README](../README.md)) makes the next step straightforward:

- **Agentic toolset.** The retrieval, breadth routes (statistics,
  comparison, draft, year), and offer-detail lookups are already
  structured, testable functions. The plan is to expose them as tools for
  an LLM agent that can plan multi-step queries — e.g. *merge data points
  across multiple offers* (combined scope, overlapping line items,
  cross-offer price trends) instead of answering from a single top-k
  retrieval.
- **Cross-offer synthesis.** Today's comparison route aggregates
  pre-retrieved chunks; an agent could iteratively retrieve, reconcile
  conflicting terms, and produce a consolidated view over an entire offer
  portfolio.
- **Revisiting the framework decision.** If the agentic layer grows,
  adopting a framework (e.g. LlamaIndex agents or similar) at the
  orchestration level — while keeping the retrieval core hand-rolled —
  is a realistic option.

## Layout

```
docs/
├── OVERVIEW.md                this overview
├── data-journey.svg           data journey diagram (embedded in the root README)
├── adr/                       architecture decision records (index + 5 ADRs)
└── local-inference/
    ├── SETUP.md               vLLM + Ollama setup guide (on-prem)
    ├── grafana-monitoring-2026-08-30.png
    └── byok-vscode-2026-08-30.png
```
