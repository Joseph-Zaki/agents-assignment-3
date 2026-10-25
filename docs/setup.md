# Setup

Get the n8n container running, configure credentials, and confirm the workflow loads.

---

## 1. Pinned versions

| Component | Version authored against |
|-----------|--------------------------|
| n8n image | `docker.n8n.io/n8nio/n8n:2.19.5` (pinned in `docker-compose.yml`) |
| Anthropic model | `claude-sonnet-4-6` |
| Anthropic API version | `2023-06-01` |

If your n8n boots a meaningfully newer version (>=3.x), the workflow will probably still import — n8n is good at backwards compatibility — but expect minor warnings. Note any version drift in your `analysis.md`.

---

## 2. Prerequisites

You should already have:

- Docker Desktop installed and running (covered in the Week 3 lecture handout)
- An Anthropic API key with available credit (course-issued)

Verify Docker:

```bash
docker --version
docker compose version
```

---

## 3. First-time bring-up

From the assignment-3 root:

```bash
cp .env.example .env
openssl rand -hex 32   # copy the output into N8N_ENCRYPTION_KEY in .env
docker compose up -d
```

First boot pulls the image (~400 MB) and runs DB migrations. Give it 60–90 seconds.

The startup script auto-imports any JSON files in `workflows/` on first boot. You should see two workflows once you log in:

- **Topic Planner (Claude)** — the warm-up demo from the base setup
- **Supply Chain Manager (Starter)** — the assignment

Confirm via the editor at [http://localhost:5678](http://localhost:5678). On first visit you'll create a local owner account (email + password) — this is the only auth in front of n8n; it lives in the SQLite DB inside the `n8n_data` volume and is independent of anything online.

---

## 4. Configure your Anthropic credential

The workflow's five LLM nodes all reference a Header Auth credential named **`Anthropic API Key`**. Create it once and they'll all link automatically.

1. **Overview** → **Credentials** tab → **Create credential** (**Add first credential** if the list is empty) → search **Header Auth** → **Continue**
2. **Credential Name:** `Anthropic API Key`  *(this name is significant — the workflow looks it up by name)*
3. **Name:** `x-api-key`
4. **Value:** `sk-ant-...your-key...`
5. **Save**

Open the **Supply Chain Manager (Starter)** workflow and click any LLM node (e.g. **Master Planner Agent**). The credential dropdown should already show `Anthropic API Key` selected. If it shows "Select credential" instead, pick it manually — n8n usually auto-links by name on import but doesn't always.

---

## 5. Demo data

The four CSVs are bind-mounted into the container at `/data/`:

| Path inside container | What it is |
|-----------------------|------------|
| `/data/sales_history.csv` | 12 months × 15 SKUs, with seasonality + a viral spike + a decline |
| `/data/current_inventory.csv` | Current on-hand, reorder point, lead time, costs |
| `/data/suppliers.csv` | 6 suppliers across 4 regions with reliability/quality KPIs |
| `/data/shipping_options.csv` | 10 carriers across air/ocean/ground |

The workflow's four "Read … File" nodes already point at these paths. You should not need to change them.

To peek at the raw data without leaving your terminal:

```bash
head data/sales_history.csv
```

---

## 6. Trigger your first run (and see it break)

In the editor, with the **Supply Chain Manager (Starter)** workflow open:

1. Click **Test workflow** (bottom of the canvas).
2. The trigger fires; the four CSV reads succeed; the Build Context Summary node returns headline stats; the Master Planner LLM call goes out to Anthropic.
3. **Expected first failure:** the Parse Plan node fails with "Planner did not return valid JSON. See the Master Planner Agent output for the raw reply." because your planner's system prompt is still a TODO and the model returns prose instead of the required JSON shape.

This is correct. Open the Master Planner Agent node, fill in **MP-1** (system prompt schema), Save, and re-run. You should now get past Parse Plan; the Switch routes to whichever subgoal your planner picked; that branch executes until it hits its own TODO.

Each TODO you implement gets you one node further.

---

## 7. Re-importing after editing the JSON

If you edit `workflows/supply-chain-manager-starter.json` outside the editor (you usually shouldn't — edit in n8n and let the editor manage the JSON), the auto-importer needs its marker cleared to re-import:

```bash
docker exec n8n rm /home/node/.n8n/.imported_supply-chain-manager-starter.json
docker compose restart n8n
```

If you started the container before the image was pinned to `2.19.5`, pull the update, run the `docker exec ... rm` line above, then run `docker compose up -d` instead of `restart`: it switches to the pinned image and re-imports the corrected starter. Re-importing replaces the starter workflow in n8n, so export any edits you made in the editor first.

To wipe everything (workflows, credentials, owner account) and start fresh:

```bash
docker compose down -v   # the -v removes the named volume — workflows and credentials are GONE
docker compose up -d
```

---

## 8. Common issues

| Symptom | Likely cause / fix |
|---------|--------------------|
| Workflow not on the Overview page after `up -d` | Auto-import failed silently — check `docker compose logs n8n \| grep import` |
| LLM node shows "Credential not found" | You haven't created the **Anthropic API Key** credential, or you named it differently |
| Parse Plan fails with "Planner did not return valid JSON. See the Master Planner Agent output for the raw reply." | Master Planner prompt isn't constraining the output — open MP-1 and reread the schema requirements |
| Parse Logistics Decision fails with "Logistics Coordinator did not return valid JSON", "Logistics Coordinator returned no decision object for REQ-..." or "Logistics Coordinator returned use_classical_fallback = ..." | Logistics Coordinator prompt (LG-1, LG-3) isn't constraining the output. Make it return one raw JSON object per request, with `use_classical_fallback` as a boolean `true`/`false`, not the string `"true"` |
| `port is already allocated` on `up -d` | Another process is on 5678 — stop it, or change the host-side port mapping in `docker-compose.yml` |
| All LLM nodes return 401 | Bad `x-api-key` value in your credential — re-paste from the Anthropic console |
| Code node fails with `implement <function>()`, with `TODO [easy\|medium\|hard]` under it | This is intended. Implement the corresponding TODO in the matching `custom-nodes/*.js`. |

---

## 9. Cost watch

While iterating, prefer **Execute Node** (one node at a time) over **Test workflow** (the whole graph). A single LLM call is ~$0.01–$0.02; full runs are ~$0.05–$0.10 (a single subgoal branch fires per run).

If you need to debug the planner prompt many times in a row, drop the temperature in the HTTP body to 0 and shorten the system prompt — both reduce token cost without changing what you're testing.
