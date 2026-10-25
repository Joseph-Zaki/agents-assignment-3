# Week 3 In-Class Exercise: Smart Order Router

A 30-minute hands-on. You import a fully-built n8n workflow, fire test orders at it via webhook, and observe how the agent reasons about routing. No code to write — the goal is to **read the workflow, predict its behavior, and modify pieces** to see how planning patterns compose.

---

## What you'll see

A 12-node workflow that takes an order JSON over webhook → asks Claude to classify it as **urgent / standard / bulk** → routes to the matching warehouse → checks stock → either confirms or falls back to an alternative warehouse → logs the decision with reasoning trace.

```
[Order Webhook]
       ↓
[Normalize Order]              ← parses payload, attaches mock inventory
       ↓
[AI Order Classification]      ← Claude Sonnet 4.6 returns priority JSON
       ↓
[Parse Classification]
       ↓
[Route by Priority] (Switch)
   ├─ urgent   → [Pick Warehouse A (Express)]   ─┐
   ├─ standard → [Pick Warehouse B (Standard)]  ─┤
   └─ bulk     → [Pick Warehouse C (Bulk)]      ─┘
                                                  ↓
                                          [Stock Available?] (IF)
                                            ├─ true  → [Mark Routed]
                                            └─ false → [Alternative Sourcing]
                                                          ↓
                                                  [Log Decision]
                                                          ↓
                                                  (webhook response)
```

---

## Setup (5 min)

1. n8n container running locally (`docker compose up -d` from the repo root). The workflow auto-imports on first boot.
   If your container was already running before you pulled this week's update, re-import the corrected workflow: `docker exec n8n rm /home/node/.n8n/.imported_smart-order-router-inclass.json`, then `docker compose restart n8n` (or `docker compose up -d` if you started before the image was pinned to 2.19.5, see `docs/setup.md` section 7). Re-importing unpublishes the workflow, so do step 5 again afterwards.
2. Open [http://localhost:5678](http://localhost:5678) → sign in to your owner account.
3. **Smart Order Router (In-Class)** should appear on the **Overview** page (Workflows tab).
4. **Create the Anthropic credential** (one-time, shared with the homework workflow):
   - **Overview** → **Credentials** tab → **Create credential** (**Add first credential** if the list is empty) → search **Header Auth** → **Continue**
   - Credential name (the title at the top of the dialog): `Anthropic API Key`
   - **Name:** `x-api-key`, **Value:** `sk-ant-...` (the field labeled Name is the header name, not the credential name). Then **Save**.
5. **Publish the workflow**: open it, check that the **AI Order Classification** node's Credential field shows `Anthropic API Key` (select it if not), then click **Publish** in the top-right of the canvas. n8n 2.x replaced the old Active toggle with Publish. The webhook URL is now live.

---

## Trigger your first order (2 min)

The webhook is at `http://localhost:5678/webhook/smart-order-router`. Send a VIP order:

```bash
curl -sS -X POST http://localhost:5678/webhook/smart-order-router \
  -H "content-type: application/json" \
  -d '{
    "order_id": "ORD-001",
    "customer_id": "CUST-99",
    "customer_tier": "vip",
    "items": [{"sku": "SKU-001", "quantity": 2}],
    "shipping_method": "express",
    "order_value": 750
  }' | jq
```

Expected: priority comes back `urgent`, assigned warehouse `WAREHOUSE_A`, action `routed_primary`. Open the Executions list (left sidebar) and click into the run — you'll see each node's input and output.

---

## The four scenarios (15 min)

Run each in turn. Open the latest execution after each one and **predict the output before reading it.**

### Scenario 1: VIP express
The curl above. Expected route: urgent → WAREHOUSE_A. Stock available.

### Scenario 2: Standard customer

```bash
curl -sS -X POST http://localhost:5678/webhook/smart-order-router \
  -H "content-type: application/json" \
  -d '{
    "order_id": "ORD-002",
    "customer_tier": "regular",
    "items": [{"sku": "SKU-002", "quantity": 5}],
    "shipping_method": "standard",
    "order_value": 80
  }' | jq
```

Expected: standard → WAREHOUSE_B.

### Scenario 3: Wholesale bulk

```bash
curl -sS -X POST http://localhost:5678/webhook/smart-order-router \
  -H "content-type: application/json" \
  -d '{
    "order_id": "ORD-003",
    "customer_tier": "wholesale",
    "items": [{"sku": "SKU-002", "quantity": 100}],
    "shipping_method": "standard",
    "order_value": 2400
  }' | jq
```

Expected: bulk → WAREHOUSE_C.

### Scenario 4: Out of stock — fallback path

```bash
curl -sS -X POST http://localhost:5678/webhook/smart-order-router \
  -H "content-type: application/json" \
  -d '{
    "order_id": "ORD-004",
    "customer_tier": "vip",
    "items": [{"sku": "SKU-002", "quantity": 1}],
    "shipping_method": "overnight",
    "order_value": 600
  }' | jq
```

`SKU-002` is out of stock at `WAREHOUSE_A` (the urgent lane). Expected: priority urgent → assigned A → in_stock=false → fallback to WAREHOUSE_B (or C). Action: `fallback_routed`.

---

## Now break it (8 min)

Pick at least two of the following and observe. After each edit, click **Publish** again before you re-run a curl: the `/webhook/` URL runs the last published version of the workflow, not your saved edits.

| Modification | What to watch |
|--------------|---------------|
| Edit the **AI Order Classification** node — soften "urgent" to require `order_value > 1000`. Re-run scenario 1. | Does the priority change to standard? Does Claude follow your new rule precisely or hallucinate? |
| Edit the **Normalize Order** node — set every SKU in every warehouse to `0`. Re-run scenario 2. | Does the workflow correctly escalate to manual review? What's in the response? |
| Add a 4th branch in **Route by Priority** for `priority = "subscription"`, then ask Claude (in the system prompt) to also classify subscription orders. Run a test order with `customer_tier: "subscription"`. | What happens if Claude returns a value the Switch doesn't have a rule for? (Look at the "extra" fallback output.) |
| Lower `max_tokens` in **AI Order Classification** to `50`. Re-run any scenario. | What does truncated JSON do to the Parse Classification node downstream? |
| Add a `confidence_threshold` check after Parse Classification — if `classification_confidence < 0.7`, route to manual review. | This is a small new IF node. Where would it best fit in the topology? |

---

## Discussion prompts (last 5 min)

1. The **Route by Priority** Switch routes on `$json.priority`. The classifier emits this as text. What's the failure mode if the model returns `"urgent "` (trailing space) or `"Urgent"` (capitalized)? How would you defend against it?
2. The **Stock Available?** IF node only checks one boolean. If a customer orders 5 SKUs and 4 are in stock, what should happen? The current workflow treats "any item missing" as out-of-stock — is that the right default?
3. Where in this workflow does **classical logic** make decisions, and where does **the LLM** make decisions? Could you swap their roles?
4. If you were paged at 3am because this workflow misrouted 200 orders, what's the **first node** you'd inspect, and why?

These same patterns scale to the homework supply-chain manager — the difference is one Switch routes on classifier output, the other on planner output.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| curl gets 404 `The requested webhook "POST smart-order-router" is not registered.` | Workflow isn't published. Open it and click **Publish** in the top-right (n8n's hint still says "activate the workflow using the toggle"; in 2.x that control is Publish). |
| AI Order Classification fails with `Credential with ID "anthropic-credential-placeholder" does not exist for type "httpHeaderAuth".` | The published version still points at the placeholder credential from the import. Open AI Order Classification, select `Anthropic API Key` in the Credential field, then click **Publish** again. |
| Your edit doesn't change the curl response | You saved but didn't re-publish. The `/webhook/` URL runs the last published version; click **Publish**. |
| LLM call returns 401 | The `Anthropic API Key` credential is missing or has a bad key. Re-paste from the Anthropic console. |
| Parse Classification fails with "Classifier did not return valid JSON. See the AI Order Classification output for the raw reply." (the curl gets `{"message":"Error in workflow"}`) | Claude wrapped the response in markdown fences or added prose. The reply is under the error message and in the AI Order Classification output. Open that node and re-emphasize "RAW JSON, no fences" in the system prompt. |
| Inventory check always says `false` | You're using a SKU not in the mock inventory (`SKU-001`/`-002`/`-003` only). Check Normalize Order. |
| Test orders not appearing in Executions | The workflow isn't published OR you're hitting `/webhook-test/` instead of `/webhook/`. |

---

## What this exercise teaches

- **Webhook → workflow → response** as the basic event-driven n8n pattern.
- **LLM as a classifier** — single call, structured JSON output, deterministic downstream routing.
- **Switch routing on a model-emitted field** — the fragile seam between LLM output and graph control flow.
- **IF + fallback path** — graceful degradation when assumptions fail.
- **Audit logging** — turning a planning decision into a structured record.

These are the same primitives you'll use in the homework, just with planner-emitted subgoals instead of classifier-emitted priorities.
