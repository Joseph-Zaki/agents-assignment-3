# Assignment 3: Intelligent E-commerce Supply Chain Manager

**UCLA Extension - Agentic AI Course · Week 3: Planning & Reasoning**

---

## 1. Learning Objectives

By the end of this assignment you will be able to:

- **LO-1.** Decompose a high-level business goal into ordered subgoals using a Hierarchical Task Network (HTN) pattern, expressed as a structured LLM output that downstream nodes can route on.
- **LO-2.** Implement a closed-form classical optimization (EOQ) and a classical search baseline (greedy carrier assignment), and articulate why each is preferred to an LLM in its specific domain.
- **LO-3.** Build a classical statistical forecast (moving average × seasonal index) and explain the assumptions behind it.
- **LO-4.** Detect when a classical model's assumptions break, and design the routing logic that hands those cases to an LLM exception handler.
- **LO-5.** Design LLM prompts that operate at the seam between classical and LLM-based planning — taking numerical outputs as input and producing structured, schema-conformant JSON for downstream consumption.

The lecture material and `docs/planning-primer.md` cover the academic framing — read both *before* you start coding.

---

## 2. Business Scenario

You're the new operations engineer at **Coastal Goods**, a mid-sized e-commerce company selling 15 SKUs across summer, winter, and evergreen categories. You have one year of sales history, a current inventory snapshot, six suppliers across four regions, and a catalogue of ten shipping options.

Two situations are quietly developing in the data:

1. **One SKU is going viral** — month-over-month demand more than doubled in September and is still climbing. Inventory is well below the reorder point. If your forecaster only looks at the trailing average it will completely miss this.
2. **One SKU is dying** — a 12-month linear decline. Inventory sits at 6.8× the reorder point. EOQ will happily recommend reordering more.

Your job is to build a planning agent that finds *both* of these and recommends correct actions — viral product gets an emergency reorder, declining product gets a markdown — without you hand-coding "if SKU == 'X' then ...". The orchestration must generalize.

---

## 3. The Five Components

The starter workflow ships the five-component topology with all wiring in place. You implement what flows through it.

| # | Component | Type | What you implement |
|---|-----------|------|-------------------|
| 1 | **Master Planner Agent** | LLM (Anthropic Sonnet) | System prompt: hierarchical decomposition + JSON schema with `next_subgoal` field |
| 2 | **Demand Forecasting Engine** | Code (JS) + LLM | `movingAverage()`, `seasonalIndex()`, then a context-adjustment LLM prompt |
| 3 | **Inventory Optimization Planner** | Code (JS) + LLM | `eoq()` formula, `detectViolations()` heuristics, then an exception-handling LLM prompt |
| 4 | **Supplier Performance Monitor** | LLM | A scoring rubric across cost / lead time / reliability / quality with explicit weights |
| 5 | **Logistics Coordinator** | LLM + classical fallback Code | Soft-constraint LLM prompt + `pickCheapestFeasible()` greedy planner |

The Switch node downstream of the Master Planner routes to one of the four leaf branches based on the field your planner emits. The IF node downstream of the Logistics LLM routes to the classical fallback when your prompt sets `use_classical_fallback: true`.

You will not need to add or remove any nodes. If you find yourself wanting to, re-read the topology — the assignment is about building the *contents*, not redesigning the orchestration.

---

## 4. TODO Inventory (100 points)

Each TODO is tagged with a difficulty marker and a learning objective. Sequence by difficulty if you want incremental wins; otherwise sequence by component if you prefer to finish one piece at a time.

### Master Planner Agent — 18 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| MP-1 | System prompt: define output JSON schema with `next_subgoal` | easy | LO-1 | 8 |
| MP-2 | System prompt: add 1-2 worked HTN-style decomposition examples | medium | LO-1 | 10 |

### Demand Forecasting Engine — 18 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| DF-1 | `demand-forecast.js` `movingAverage()` | easy | LO-3 | 6 |
| DF-2 | `demand-forecast.js` `seasonalIndex()` | medium | LO-3 | 8 |
| DF-3 | LLM prompt: contextual revision of the numeric forecast | easy | LO-5 | 4 |

### Inventory Optimization Planner — 22 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| EOQ-1 | `eoq-optimizer.js` `eoq()` formula | medium | LO-2 | 8 |
| EOQ-2 | `eoq-optimizer.js` `detectViolations()` | hard | LO-4 | 10 |
| EOQ-3 | LLM prompt: per-flag exception action | easy | LO-4 | 4 |

### Supplier Performance Monitor — 14 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| SP-1 | LLM prompt: 4-dimension rubric with weights | medium | LO-5 | 14 |

### Logistics Coordinator — 18 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| LG-1 | LLM prompt: hard + soft constraint reasoning | easy | LO-5 | 6 |
| LG-2 | `classical-logistics.js` `pickCheapestFeasible()` | hard | LO-2 | 10 |
| LG-3 | LLM prompt: emit `use_classical_fallback: true` when appropriate | easy | LO-4 | 2 |

### Final synthesis — 10 pts
| ID | Where | Difficulty | LO | Pts |
|----|-------|------------|----|-----|
| FN-1 | `Final Output` Code: aggregate into business-readable summary, set `next_recommended_subgoal` | medium | LO-1 | 10 |

**Total: 13 TODOs, 100 points.** Difficulty mix: 6 easy / 5 medium / 2 hard.

(LO-tag legend: LO-1 hierarchical decomposition · LO-2 classical optimization · LO-3 classical statistics · LO-4 assumption-boundary detection · LO-5 LLM-classical seam.)

---

## 5. How to Run

`docs/setup.md` walks you through bringing up the local n8n container and importing the workflow. Once it's open in the editor, you'll iterate:

1. Pick a TODO.
2. Edit the relevant Code node OR system prompt in the n8n UI.
3. **Always mirror Code-node changes back to the matching `custom-nodes/*.js` file** — that's what gets reviewed.
4. Click **Test workflow** to run end-to-end, or **Execute Node** to test one component in isolation.
5. Inspect the node's output panel to see whether your change behaves as expected.

Expect the first run to fail — that's the design. The first algorithm Code node throws `Error: TODO ...` until you implement it. Each TODO you complete gets you one node further before the next one breaks. You are done when each of the four branches has run end to end in at least one of your runs (vary the goal to drive the planner to different `next_subgoal` choices).

---

## 6. Cost Budget

**Target: under $0.10 per end-to-end run** with Claude Sonnet 4.6.

Per-run estimate at expected token volumes:
- Master Planner: ~2K in / 1K out ≈ $0.021
- Forecast Adjuster: ~1K in / 0.5K out ≈ $0.011
- Inventory Exception: ~1K in / 0.5K out ≈ $0.011
- Supplier Score: ~2K in / 1K out ≈ $0.021
- Logistics: ~1.5K in / 1K out ≈ $0.020

Total: ~$0.085. Test workflows aggressively while developing — but each run hits at most one branch (the Switch routes to one path), so single-branch tests are well under $0.05.

If your runs exceed this budget, your prompts are too verbose. Trim before tuning anything else.

**Grading note (Oct 16, 2026):** the forecast and inventory branches call Claude once per SKU (15 calls per run), so those runs can cost more than $0.10. There is no deduction for that. Report your real cost per run in `analysis.md`.

---

## 7. Submission

See `docs/submission.md` for the full file list and process. In short you submit:
1. The completed `workflows/supply-chain-manager-starter.json`
2. The three `custom-nodes/*.js` files with your implementations
3. An `analysis.md` (described in `submission.md`) covering algorithm comparison and run metrics
4. A short demo video (≤ 5 minutes)

---

## 8. Rubric Summary (100 pts)

| Area | Pts |
|------|----|
| TODO completion (per the breakdown above) | 100 baseline — partial credit per TODO |
| Code clarity and comments | folded into per-TODO partial credit |
| Reflective `analysis.md` quality | required to receive credit on EOQ-2, MP-2, SP-1 |
| Demo video shows a working end-to-end run of the branch the planner picks, plus one other branch (see `submission.md` section 5) | required to unlock full credit on MP-1 and FN-1 |

Reasonable, well-reasoned departures from the suggested approaches earn full credit if you defend them in `analysis.md`. The rubric rewards understanding the trade-offs more than reproducing one specific implementation.

---

## 9. Constraints (don't drift)

- **No new external services.** Everything you need is in `data/`. Don't add Shopify, real shipping APIs, vector stores, or RAG. The lesson is planning and reasoning, not retrieval.
- **No webhooks, no scheduling, no n8n Cloud.** This runs on your laptop in the Docker container we set up.
- **Use Anthropic Claude Sonnet 4.6** for all LLM nodes — already pinned in the workflow JSON. Don't change models without justifying it in `analysis.md` (cost or capability claim).
- **Don't redesign the topology.** The HTN shape is the lesson; build inside it.

---

## 10. Where to Get Unstuck

- `docs/planning-primer.md` — the readings supplement. Re-read the section that maps to your current TODO's LO tag.
- The inline comments in the Code nodes and system prompts. They contain hints, not just docstrings.
- Office hours. The TODOs are designed to be independently testable — bring the specific node output that surprised you.

Do not submit issues or PRs against the starter repo. Treat it as immutable.
