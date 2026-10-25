# Submission

What to submit, where, and what the grader is looking for.

---

## 1. Get your own copy of the starter

Two equivalent ways — pick whichever fits how you work:

**Option A — Fork (recommended if you already have a GitHub account)**
1. Go to the assignment repo on GitHub and click **Fork**.
2. Clone your fork locally and start working on `main` (or a branch — the grader looks at whichever branch you submit).

**Option B — Clone + push to your own repo**
1. Clone the assignment repo from GitHub.
2. Create a new **public** repository under your own GitHub account.
3. `cd agent-assignment-3 && git remote set-url origin <your-new-repo-url> && git push -u origin main`

**Your repository must be public.** The grader pulls anonymously — private repos can't be accessed without managing collaborator invitations, which we won't do. If you have a strong reason to keep it private (e.g. an existing employer policy), email the course staff before you start.

Either way, you submit by pasting the URL of your repo into the Canvas assignment page when you're done.

## 2. Files in your final submission

Push the following to whichever branch you'll submit:

| Path | Contents |
|------|----------|
| `workflows/supply-chain-manager-starter.json` | Your completed workflow, exported from n8n |
| `custom-nodes/demand-forecast.js` | Your implementations of `movingAverage` and `seasonalIndex` |
| `custom-nodes/eoq-optimizer.js` | Your `eoq` and `detectViolations` |
| `custom-nodes/classical-logistics.js` | Your `pickCheapestFeasible` |
| `analysis.md` | Your written reflection (see §4 below) |
| `demo.mp4` *(or a link in `analysis.md` to a Loom/YouTube video)* | ≤ 5-minute screencast |

You do NOT need to commit your `.env` (it's already gitignored), the `data/` CSVs (we have the originals), or the `docs/` folder.

---

## 3. Exporting your workflow

In n8n: open **Supply Chain Manager (Starter)** → top-right ⋮ menu → **Download** → save the file over `workflows/supply-chain-manager-starter.json` in your local clone. Commit it.

Make sure your Code-node JS is also committed in the matching `custom-nodes/*.js` files. The grader cross-references the two: if your in-workflow JS differs from the file (other than whitespace), the file is treated as authoritative for partial-credit calculation.

---

## 4. `analysis.md` (required, ~800–1200 words)

Half of the per-TODO points carry a "must be defended in `analysis.md`" requirement (specifically MP-2, EOQ-2, and SP-1 — see the rubric in `assignment.md`). Cover the following sections:

### 4.1 Algorithm comparison (300–400 words)

Pick *one* SKU from your forecast output and compare:
- The classical baseline (your `movingAverage` × `seasonalIndex` for that SKU)
- The LLM-revised forecast (output of the Forecast Context Adjuster)

For each, note:
- The numeric value
- The reasoning (where the LLM revision came from, where the classical number came from)
- Which one you'd actually trust to size your next reorder, and why

If you picked SKU-007 or SKU-013 (the obvious anomaly cases), do this for one of them and one well-behaved SKU so the contrast is visible.

### 4.2 EOQ assumption analysis (200–300 words)

For your `detectViolations()`, list each flag you implemented and:
- The threshold you chose
- One SKU in `data/current_inventory.csv` that triggers it
- The action your downstream LLM exception handler recommends, and whether you agree

If you decided NOT to implement a particular check (e.g. perishability — none of our demo data is perishable), say so explicitly and explain.

### 4.3 Supplier rubric defense (150–250 words)

Justify your weighting across the four dimensions (cost / lead time / reliability / quality). Specifically:
- Total = 100; what fraction did each dimension get?
- Why? (an e-commerce DTC company will weight differently than a hospital supply chain — name your assumed business model)
- Show your top-ranked and bottom-ranked supplier from a real run, and confirm the ranking matches your intuition

### 4.4 Run metrics (100–200 words)

From at least three end-to-end runs (cover at least three of the four `next_subgoal` branches across them):
- Total tokens consumed (sum across all LLM calls in the run)
- Approximate dollar cost
- Wall-clock latency end-to-end
- Anything that surprised you

The expected envelope is ~$0.05–$0.10 per run. If you blew through it, name the cause.

### 4.5 Reflection on the four primer questions (100–200 words)

`docs/planning-primer.md` §8 lists four questions. Answer them. Brief, direct.

---

## 5. Demo video (≤ 5 minutes)

Record a screencast that shows:

1. (15s) The five components of your workflow in the canvas
2. (45s) Triggering a run, showing the Master Planner output and the `next_subgoal` decision
3. (60s) The branch that executes — pause on the LLM node's output and the Code node's output
4. (60s) ONE other branch (re-run with a different goal that drives the planner to a different subgoal)
5. (90s) Walk through SKU-007 and/or SKU-013 — show that your system catches them appropriately

You don't need to narrate every line; demonstrate that the system works end-to-end and that you understand what each piece is doing.

Loom or YouTube unlisted is fine. If linking, paste the URL in `analysis.md` under a heading "## Demo video".

---

## 6. Submitting via Canvas

When you're ready, submit the URL of your repository (your fork, or the new repo you pushed your clone into) via the Canvas assignment page. The grader pulls from that URL.

```bash
git add workflows/ custom-nodes/ analysis.md demo.mp4
git commit -m "Submit assignment 3"
git push origin main          # or whichever branch you're submitting
```

You can push multiple times before the deadline; the grader uses the **last commit on your submitted branch as of the deadline**. If you submit a tag instead of a branch (`v1.0`, etc.), make sure the tag is pushed.

**Repository must be public.** The grader pulls anonymously over HTTPS. If your repo is private when you submit the URL, the grader will mark it ungradable and follow up — not what you want the day before the deadline.

---

## 7. What graders DO NOT want to see

- A reference solution copied from elsewhere. Failing-but-honest implementations earn more points than working-but-borrowed ones.
- TODO comments still present in submitted code. If you didn't implement one, leave the `throw new Error("TODO ...")` AND say so in `analysis.md`. Empty TODOs cost less than fake implementations.
- A workflow with the topology rewired. You're graded on the contents of the five components, not on alternative orchestrations.
- LLM prompts >500 words. Long prompts almost always indicate lack of clarity in the schema. The model needs the schema and a few-shot example, not your entire mental model.
- A new model swap (e.g. GPT-4 instead of Claude Sonnet) without a defended reason in `analysis.md`. The cost analysis depends on a stable model.

---

## 8. Honor code

Standard course policy. Discussion with classmates is fine; copying their workflow JSON or JS is not. If two submissions converge on identical schema or prompt text, you'll both be asked to defend it in office hours.
