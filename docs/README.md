# Documentation (Sidequest)

This folder documents **what made the project possible** — the infrastructure
and the process around the application itself. The app and the notebooks are
the deliverable; this is the story of how they were built and how the
inference stack behind them was set up.

## Contents

| Topic | What it covers |
|---|---|
| [`local-inference/`](local-inference/README.md) | The self-hosted LLM endpoint: vLLM on a 2-GPU machine (systemd service, tuned serving flags, monitoring) and Ollama as the no-GPU alternative — plus how the app and notebooks wire into it |
| [`local-inference/`](local-inference/README.md) § BYOK | Proof: the entire repository was developed with an **on-prem coding agent** — VS Code wired via BYOK to the same self-hosted vLLM endpoint, no cloud LLM involved (screenshots in the guide) |

## How this project was built

**Self-hosted, self-tuned, end to end.** Every LLM call that went into this
repository — the pipeline notebooks, the app development, the code review —
ran against the on-prem vLLM server described in
[`local-inference/`](local-inference/README.md). No cloud API was used at
any point during development.

![The on-prem coding agent at work](local-inference/byok-vscode-2026-08-30_02-56-47.png)

<em>The on-prem coding agent at work — VS Code wired via BYOK to the self-hosted vLLM endpoint.</em>

Two things worth calling out:

1. **The application** (Streamlit app + pipeline notebooks) was written and
   iterated on with a coding agent that talks to the local vLLM endpoint —
   the same endpoint the finished app uses in production.
2. **Bringing up the inference machine is a project in itself.** The vLLM
   setup — 2-GPU tensor parallelism, FP8 KV cache, speculative decoding,
   reasoning-effort tuning, systemd service, Grafana monitoring — is
   documented in [`local-inference/`](local-inference/README.md) and is a
   reusable result on its own: any similar RAG or agent workload on your own
   hardware can start from that configuration.

## Layout

```
docs/
├── README.md                  this overview
└── local-inference/
    ├── README.md              vLLM + Ollama setup guide (on-prem)
    ├── grafana-monitoring-2026-08-30.png
    └── byok-vscode-2026-08-30.png
```
