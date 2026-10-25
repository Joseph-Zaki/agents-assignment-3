# Assignment 3: Intelligent E-commerce Supply Chain Manager

**UCLA Extension - Agentic AI Course · Week 3: Planning & Reasoning**

Build a hybrid planning agent in **n8n** that decomposes a high-level supply-chain goal into ordered subgoals, mixes classical algorithms (moving average, EOQ, greedy search) with LLM reasoning at the right seams, and produces an auditable plan.

## Start here

➡️ **[`docs/assignment.md`](docs/assignment.md)** — full take-home assignment spec, learning objectives, the 13 TODOs with point values, rubric.

Then, in order:
- [`docs/planning-primer.md`](docs/planning-primer.md) — academic framing (HTN, STRIPS, classical vs LLM, hybrid patterns)
- [`docs/setup.md`](docs/setup.md) — local n8n bring-up, credentials, first run
- [`docs/submission.md`](docs/submission.md) — what to submit and how

**For the in-class exercise** (separate from the homework): [`docs/in-class.md`](docs/in-class.md) — fully built **Smart Order Router** workflow that auto-imports alongside the homework starter; you trigger it via webhook, observe routing, and modify pieces. ~30 minutes.

## Quick bring-up

```bash
cp .env.example .env
openssl rand -hex 32          # paste into N8N_ENCRYPTION_KEY in .env
docker compose up -d
```

Then open [http://localhost:5678](http://localhost:5678), create a local owner account, and add an **Anthropic API Key** Header Auth credential. The starter workflow auto-imports on first boot. Detailed walkthrough in [`docs/setup.md`](docs/setup.md).

## Repo layout

```
.
├── docs/                     spec, primer, setup, submission
├── workflows/
│   ├── supply-chain-manager-starter.json   the homework (auto-imported)
│   ├── smart-order-router-inclass.json     the in-class exercise (auto-imported)
│   └── topic-planner.json                  warm-up demo
├── custom-nodes/             canonical JS sources for the Code nodes
├── data/                     demo CSVs (sales, inventory, suppliers, shipping)
├── docker-compose.yml        single-container n8n + auto-import + data mount
├── build_workflow.py         regenerates the workflow JSON from custom-nodes/*.js
├── .env.example
└── .gitignore
```

## What you build

Five components inside an HTN-shaped orchestration. The topology is given; you fill in the contents.

| Component | Type | What you implement |
|-----------|------|--------------------|
| Master Planner Agent | LLM | Hierarchical decomposition + JSON schema with `next_subgoal` |
| Demand Forecasting Engine | Code (JS) + LLM | `movingAverage`, `seasonalIndex`, then a context-adjustment prompt |
| Inventory EOQ Planner | Code (JS) + LLM | `eoq` formula, `detectViolations`, then an exception-handling prompt |
| Supplier Performance Monitor | LLM | A 4-dimension scoring rubric with explicit weights |
| Logistics Coordinator | LLM + classical fallback Code | Soft-constraint prompt + `pickCheapestFeasible` greedy planner |

13 TODOs total (6 easy / 5 medium / 2 hard) — see [`docs/assignment.md`](docs/assignment.md) for the full inventory.

## Pinned versions

| | |
|---|---|
| n8n image | `docker.n8n.io/n8nio/n8n:2.19.5` (pinned in `docker-compose.yml`) |
| LLM | `claude-sonnet-4-6` |
| Anthropic API version | `2023-06-01` |

## Cost envelope

Target **under $0.10 per end-to-end run**. Each run hits one Switch branch, so single-branch debugging stays under $0.05.
