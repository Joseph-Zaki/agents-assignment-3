# Planning & Reasoning Primer

**UCLA Extension - Agentic AI Course · Week 3 supplemental reading**

This primer is the academic framing you need before you start the assignment. The course slides cover the same material at higher altitude; this document anchors the concepts in the system you're about to build.

---

## 1. Why "planning" deserves its own week

In Weeks 1 and 2 you built agents that answered questions and called tools. Each turn was reactive: take the user's input, decide which tool to call, return a response. That's enough for narrow assistants but not enough for *operations*.

A real supply-chain operator doesn't answer questions one at a time. They look at a goal — *"prepare a Q1 inventory plan"* — and decompose it into ordered work: forecast demand → check inventory → flag exceptions → score suppliers → commit shipments. The order matters because each step's output is another step's input. You can't optimize inventory before you know what demand will be.

That kind of *goal-conditioned, multi-step, dependency-aware* behavior is what the planning literature has been studying since the 1970s. Modern LLM agents bring new capabilities to it but also new failure modes. This week is about understanding both.

---

## 2. Hierarchical Task Networks (HTN)

The dominant pre-LLM framework for agent planning is the **Hierarchical Task Network**. The HTN view of a problem:

- A **task** is something to accomplish (`prepare_q1_plan`).
- A task is either **primitive** (you can execute it directly: `read_csv("inventory")`) or **compound** (it must be decomposed into smaller tasks).
- A **method** is a recipe: it says "to accomplish compound task `T`, do these subtasks in this order, possibly with these preconditions."
- The **planner** recursively decomposes compound tasks until everything bottoms out in primitives.

The result is a tree (or DAG) of subgoals, with primitive actions at the leaves. The execution engine then walks the tree.

In the assignment, you can see this shape directly in the workflow:

```
prepare_q1_plan                                    [compound, root]
├── understand_demand                              [compound]
│     ├── compute_classical_forecast              [primitive — Demand Forecast Code]
│     └── adjust_for_context                      [primitive — Forecast Adjuster LLM]
├── decide_inventory_actions                       [compound]
│     ├── compute_eoq                             [primitive — EOQ Code]
│     └── handle_exceptions                       [primitive — Inventory LLM]
├── score_suppliers                                [primitive — Supplier LLM]
└── plan_logistics                                 [compound]
      ├── reason_about_trade_offs                 [primitive — Logistics LLM]
      └── (fallback) classical_assignment         [primitive — Greedy Code]
```

The Master Planner Agent is doing HTN decomposition: it takes the root goal and emits an ordered list of subgoals, picking the first unblocked one as `next_subgoal`. The Switch node is the execution engine routing to the correct primitive.

What the LLM brings to HTN that earlier planners couldn't: **the methods aren't pre-coded.** A classical HTN planner needs an exhaustive method library written by a domain expert. The LLM derives appropriate decompositions on the fly from the goal text. That generality comes at a cost — you lose the hard guarantees a finite method library gives you. (We come back to this.)

**Reading anchor:** Erol, Hendler, Nau (1994), *HTN Planning: Complexity and Expressivity*. Don't read it cover-to-cover; skim §2 for the formal model.

---

## 3. STRIPS, the canonical classical planner

Where HTN cares about *how* to decompose, **STRIPS** (Stanford Research Institute Problem Solver, Fikes & Nilsson 1971) cares about *what state changes when*. A STRIPS world is:

- A set of **propositions** describing the current state (`inventory(SKU-007) = 18`).
- A set of **operators** with three things each: preconditions (what must be true to apply), an add-list (propositions that become true), a delete-list (propositions that become false).
- A **goal** state expressed as a conjunction of propositions.

The planner searches the space of operator sequences for one that transforms the initial state into the goal state. Algorithms like A*, GraphPlan, and FF do this efficiently.

You will not write a STRIPS planner in this assignment. The reason it matters here is the **assumption discipline** STRIPS forces:

> Every operator declares exactly what it requires and exactly what it changes. If reality violates those declarations, your plan is wrong, even if every step ran.

EOQ (the formula in `eoq-optimizer.js`) is a STRIPS-style operator. Its preconditions are:

- Demand is constant
- Lead time is short relative to demand
- The item is not perishable
- Order cost and holding cost are stable and known

When those hold, EOQ gives you Q* in one line. When they don't, the *formula still computes a number* — but it's wrong, possibly catastrophically (recommend reordering 200 declining-demand wired earbuds and you've just locked up working capital for 18 months).

**This is why TODO EOQ-2 exists.** Detecting when STRIPS-style assumptions fail is half of operating any classical planner safely.

**Reading anchor:** Russell & Norvig, *AI: A Modern Approach*, ch. 11 ("Classical Planning"). The chapter on STRIPS is foundational and short.

---

## 4. Classical vs LLM-based planning

Two different tools, suited to two different conditions.

| Property | Classical (STRIPS / OR / EOQ / greedy) | LLM-based |
|----------|----------------------------------------|-----------|
| Determinism | Same input ⇒ same output | Stochastic (temperature dependent) |
| Auditability | Plan is a sequence of declared operators | Plan is a JSON blob; reasoning is in natural language |
| Cost | Compute is essentially free | API tokens, often $0.001–$0.10 per plan |
| Latency | Microseconds to seconds | Seconds to tens of seconds |
| Domain coverage | Only what the domain expert encoded | Everything the model has training data for |
| Soft constraints | Awkward — must be encoded numerically | Natural — "prefer the supplier we've worked with before" |
| Boundary handling | Crashes or returns garbage when assumptions break | Often *plausibly* wrong, which is worse than crashing |
| Explainability | Trace through the operator graph | Re-prompt the model and hope |

The supplier scoring task (component 4) and the logistics task (component 5) are good examples of where LLMs shine: **soft, multi-criteria reasoning over text-rich inputs.** A classical multi-criteria decision-making (MCDM) framework like AHP would also work, but only after you sit a domain expert down and elicit pairwise weights. The LLM gets reasonable weights from a sentence of context.

The forecasting task (component 2) and the EOQ task (component 3) are where classical wins: **deterministic, auditable, fast, free.** You don't want an LLM doing arithmetic that a moving average can do in a microsecond. You especially don't want it the day a regulator asks you why your warehouse is full.

The mistake is thinking you have to choose. The interesting systems use both.

---

## 5. Why hybrid approaches exist

A hybrid agent uses classical machinery for the *parts that are computable* and LLM reasoning for the *parts that are contextual*. Three patterns appear over and over:

### Pattern A: Classical baseline, LLM revision

The forecasting branch is this pattern. Moving-average × seasonal-index gives a reproducible numerical baseline. The LLM revises that baseline when context demands — viral TikTok mentions, a competitor going bankrupt, a heatwave. The classical layer enforces a sanity floor; the LLM layer adds the things the math cannot see.

### Pattern B: Classical solver, LLM exception handler

The inventory branch is this pattern. EOQ runs over every SKU. The Code node *also* checks each SKU against the formula's assumptions. SKUs that pass cleanly take the formula's recommendation directly — no LLM call. Only the flagged exceptions go to the LLM. This is dramatically cheaper than running an LLM over every SKU, and it makes the audit story easy: "this SKU got the EOQ recommendation; this SKU got the LLM exception path because its viral-spike flag fired."

### Pattern C: LLM router, classical executor

The logistics branch is this pattern (mostly). The LLM reasons about soft constraints and trade-offs. When the request is purely numeric (no soft constraints), the LLM emits `use_classical_fallback: true` and the IF node routes to a deterministic greedy planner. The LLM's job becomes *deciding when not to think* — and that's a perfectly good job for it.

These patterns are doing the same thing: putting LLMs where text and judgment matter, putting closed-form solvers where numbers and reproducibility matter, and being explicit about which is which.

**Reading anchor:** Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (2022). Less directly about hybrid planning, but it's the canonical statement of "let the LLM call tools instead of replacing them."

---

## 6. Multi-step reasoning and where it breaks

The Master Planner does multi-step reasoning in a single LLM call: "given this goal, derive subgoals, pick the next one." That works because the goal is small and the subgoal vocabulary is closed (four options). For larger problems, single-call decomposition struggles in two ways:

1. **Drift across steps.** If the planner emits subgoals 1-5 in one call, by step 5 it may have forgotten constraints from step 1. A safer pattern is to call the LLM again at each step with the executed-so-far history.
2. **Inconsistent vocabularies.** If the planner says `next_subgoal: "forecasting_demand"` but the Switch routes on `"forecast"`, the workflow falls through to the fallback branch silently. That's an instructive failure to leave for students. (Yes, this is on purpose. See the JSON schema TODO.)

When you complete `Final Output` (TODO FN-1), you'll add a `next_recommended_subgoal` field. That's the seed of a real planning loop — re-running the workflow with the previous-execution context advances the plan one step at a time. We don't actually wire that loop in this assignment because n8n's recursion model would distract from the lesson, but you should be able to articulate how it would work.

---

## 7. Classical search and the cost of optimality

The greedy carrier assignment in `classical-logistics.js` is the simplest classical search: enumerate, filter, pick the best. With ~10 carrier options per request and 3 requests, the entire decision space has ~30 candidates — completely searchable.

You could replace `pickCheapestFeasible` with an exhaustive search and get *provably* optimal assignments. You could go further and solve the joint problem (3 requests × 10 options = 1000 combinations) as an integer program. The answer would be globally optimal across all three requests.

We don't, for one reason: **the LLM branch needs a baseline to be compared against.** A greedy classical planner is an honest baseline. An exhaustive solver would be unfair — it would always win on cost and the LLM's value (soft constraints, explanation quality, supplier-relationship reasoning) would be invisible against it.

This is a general principle: when you build hybrid systems, give the classical and LLM branches *comparable scope*. If you give the LLM a richer search space than the classical baseline, your A/B comparison tells you nothing.

**Reading anchor:** Russell & Norvig, ch. 3 (Search). The "uninformed search" section is enough background.

---

## 8. What success looks like in this assignment

You'll know you've understood the lesson when you can answer these without looking anything up:

1. *Where in your workflow does a classical algorithm produce a wrong answer that the LLM catches, and where does the LLM produce a wrong answer that the classical layer catches?*
2. *If your Master Planner started emitting `next_subgoal: "audit_warehouse"` (a value the Switch doesn't know about), what would happen, and what change would you make to the workflow so that wasn't a silent failure?*
3. *Why does EOQ give a confident, wrong answer for SKU-013 (Wired Earbuds), and what flag in your `detectViolations()` should fire to keep that from going to production?*
4. *Why is supplier scoring an LLM job and EOQ a classical job? What would change if I asked you to swap them?*

Bring your written answers to these to your `analysis.md`. Question 2 in particular is the difference between a working agent and a *safe* agent.

---

## 9. Suggested reading order

1. This document, top to bottom — 30 minutes.
2. Russell & Norvig ch. 11 (Classical Planning), §1-3 — 45 minutes.
3. Erol et al. (1994), *HTN Planning: Complexity and Expressivity*, §2 only — 20 minutes.
4. Yao et al. (2022), *ReAct*, intro + §3 — 20 minutes.

You don't need to read these to *complete* the assignment, but the rubric items that ask for justification (MP-2, EOQ-2, SP-1) lean on this material directly.
