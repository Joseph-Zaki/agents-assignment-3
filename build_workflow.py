#!/usr/bin/env python3
"""
Builder for workflows/supply-chain-manager-starter.json.

Reads the canonical JS files from custom-nodes/ and embeds them into
the appropriate n8n Code nodes. Run after editing any *.js so the
shipped workflow stays in sync with the readable source.

Run:  python3 build_workflow.py
"""
import json
import pathlib
import uuid

ROOT = pathlib.Path(__file__).parent
NODES_DIR = ROOT / "custom-nodes"
OUT = ROOT / "workflows" / "supply-chain-manager-starter.json"


def js(name):
    return (NODES_DIR / name).read_text()


def nid(slug):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"scm-week3.{slug}"))


def pos(col, row):
    return [240 + col * 240, 200 + row * 180]


# ---- System prompts (with TODO scaffolding embedded) ----------------------

MASTER_PLANNER_SYSTEM = """You are the Master Planner Agent for an e-commerce supply-chain operation.
You receive a high-level business goal and a context summary. You decompose
the goal into ordered subgoals and decide which subgoal to dispatch first.

# TODO [easy] -- LO-1: hierarchical task decomposition
# Define the OUTPUT JSON SCHEMA. The downstream Switch node routes on the
# field `next_subgoal`. You must populate it with one of:
#   "forecast" | "inventory" | "supplier" | "logistics"
#
# Required output shape:
#   {
#     "plan_id": "<short string>",
#     "reasoning": "<2-3 sentences explaining the decomposition>",
#     "subgoals": [
#       { "id": "...", "type": "...", "rationale": "..." },
#       ...
#     ],
#     "next_subgoal": "forecast" | "inventory" | "supplier" | "logistics"
#   }
#
# Add explicit instructions to ALWAYS reply with raw JSON only -- no
# markdown fences, no preamble. The Set node downstream parses with JSON.parse.

# TODO [medium] -- LO-1: HTN-style decomposition with examples
# Provide 1-2 worked examples in the system prompt showing how a goal
# decomposes into ordered subgoals. The examples should demonstrate that
# subgoal ORDERING matters -- e.g. you can't optimize inventory before
# you have a demand forecast. Choose `next_subgoal` to be the first
# unblocked subgoal in topological order.
"""

FORECAST_ADJUSTER_SYSTEM = """You are the Forecast Context Adjuster.
You receive a numerical forecast for one SKU (computed by the upstream
classical engine) plus contextual notes. You revise the forecast when
context demands it and return JSON.

# TODO [easy] -- LO-5: hybrid reasoning at the LLM/classical seam
# Write the prompt body. Decide:
#   1. What contextual signals warrant overriding the classical forecast?
#      (Hint: viral mentions, weather anomalies, promotions, supply news.)
#   2. By how much should the LLM be allowed to deviate from the math?
#      (A 50% revision needs justification a 5% revision does not.)
#   3. Required output JSON schema:
#        { "sku", "revised_forecast", "delta_pct", "reasoning",
#          "context_signals_used" }
"""

INVENTORY_EXCEPTION_SYSTEM = """You are the Inventory Exception Handler.
You receive SKUs the EOQ formula flagged as having broken assumptions
(viral spike, declining demand, low velocity, etc.). For each, propose
an inventory action.

# TODO [easy] -- LO-4: planning when the closed-form solution doesn't apply
# Write the prompt body. Cover at minimum:
#   - "viral_spike": recommend an emergency reorder size larger than EOQ
#     suggests, because the formula's "constant demand" assumption is broken.
#   - "declining": recommend NOT reordering, possibly a markdown.
#   - "low_velocity": EOQ is numerically unstable; recommend a fixed
#     small reorder qty (e.g. 30-day demand).
# Required output JSON schema:
#   { "sku", "recommended_action": "reorder"|"markdown"|"liquidate"|"hold",
#     "recommended_qty", "reasoning" }
"""

SUPPLIER_SCORE_SYSTEM = """You are the Supplier Performance Monitor.
You receive the supplier roster with KPIs and produce scored rankings.

# TODO [medium] -- LO-5: LLM-based multi-criteria reasoning
# Design a 0-100 scoring rubric across these four dimensions and explain
# the weights you choose:
#   - cost         (proxy: payment_terms_days; longer = better cash position)
#   - lead time    (avg_lead_time_days; shorter = better)
#   - reliability  (on_time_rate; higher = better)
#   - quality      (1 - defect_rate; higher = better)
# Required output JSON schema (one object per supplier):
#   { "supplier_id", "score_total",
#     "score_breakdown": { "cost", "lead_time", "reliability", "quality" },
#     "tier": "preferred"|"approved"|"watch"|"deprioritize",
#     "recommendation": "..." }
"""

LOGISTICS_SYSTEM = """You are the Logistics Coordinator.
You receive shipping requests and the carrier catalogue. For each request
you select a carrier and explain the trade-offs.

# TODO [easy] -- LO-5: LLM-based planning with soft constraints
# Write the prompt body. Address:
#   1. Hard constraints: deadline, weight, perishability, region match.
#   2. Soft preferences: cost, transit-time risk, supplier relationships.
#   3. When two options are close on cost, prefer the one with more
#      time slack (transit_days well under deadline).
# Required output JSON schema (one per request):
#   { "request_id", "chosen_option_id", "alternatives_considered": [...],
#     "trade_off_summary": "...", "use_classical_fallback": false }
#
# Set `use_classical_fallback: true` ONLY when the request is purely numeric
# (no soft constraints) -- the IF node downstream will route those to the
# deterministic greedy planner instead.
"""

# ---- HTTP node builder for Anthropic Messages API -------------------------

def http_anthropic(name, slug, system_prompt, user_expr, col, row):
    """
    Build an HTTP Request node calling Anthropic's Messages API.
    `user_expr` is a JS expression (no surrounding quotes) that yields a
    string -- the user message body. We wrap it in JSON.stringify(...) so
    the rendered JSON is always valid regardless of newlines/quotes inside.
    """
    body = (
        '={\n'
        '  "model": "claude-sonnet-4-6",\n'
        '  "max_tokens": 2048,\n'
        '  "system": ' + json.dumps(system_prompt) + ',\n'
        '  "messages": [\n'
        '    { "role": "user", "content": {{ JSON.stringify(' + user_expr + ') }} }\n'
        '  ]\n'
        '}'
    )
    return {
        "id": nid(slug),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": pos(col, row),
        "credentials": {
            "httpHeaderAuth": {
                "id": "anthropic-credential-placeholder",
                "name": "Anthropic API Key",
            }
        },
        "parameters": {
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {"name": "anthropic-version", "value": "2023-06-01"},
                    {"name": "content-type", "value": "application/json"},
                ]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": body,
            "options": {},
        },
    }


def code_node(name, slug, code, col, row):
    return {
        "id": nid(slug),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": pos(col, row),
        "parameters": {"language": "javaScript", "jsCode": code},
    }


def set_node(name, slug, assignments, col, row):
    return {
        "id": nid(slug),
        "name": name,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": pos(col, row),
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{slug}.{a['name']}")),
                        "name": a["name"],
                        "value": a["value"],
                        "type": a.get("type", "string"),
                    }
                    for a in assignments
                ]
            },
            "options": {},
        },
    }


# ---- Build node list ------------------------------------------------------

nodes = []

# 1. Manual Trigger
nodes.append({
    "id": nid("manual"),
    "name": "Manual Trigger",
    "type": "n8n-nodes-base.manualTrigger",
    "typeVersion": 1,
    "position": pos(-1, 1),
    "parameters": {},
})

# 2. Set Goal
nodes.append(set_node(
    "Set Goal", "set-goal",
    [{
        "name": "goal",
        "value": (
            "Prepare a Q1 inventory and supplier action plan: identify SKUs "
            "at stockout risk, surface suppliers underperforming on reliability, "
            "and decide carrier coverage for the next 30 days."
        ),
        "type": "string",
    }],
    0, 1,
))

# 3-10. Four CSV reads (binary read + spreadsheet parse)
csv_paths = [
    ("Inventory", "inv", "/data/current_inventory.csv"),
    ("Sales", "sales", "/data/sales_history.csv"),
    ("Suppliers", "suppliers", "/data/suppliers.csv"),
    ("Shipping", "shipping", "/data/shipping_options.csv"),
]
for i, (label, slug, path) in enumerate(csv_paths):
    nodes.append({
        "id": nid(f"read-{slug}"),
        "name": f"Read {label} File",
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": pos(1, i),
        "parameters": {
            "operation": "read",
            "fileSelector": path,
            "options": {},
        },
    })
    nodes.append({
        "id": nid(f"parse-{slug}"),
        "name": f"Read {label} JSON",
        "type": "n8n-nodes-base.spreadsheetFile",
        "typeVersion": 2,
        "position": pos(2, i),
        "parameters": {
            "operation": "fromFile",
            "fileFormat": "csv",
            "options": {"headerRow": True},
        },
    })

# Wait for all four reads before summarizing. Wired straight into the
# single-input Code node, n8n's v1 (depth-first) order would run Build
# Context Summary once per read, the first time before Sales/Suppliers/
# Shipping have executed, and its $('Read ... JSON') references would throw.
nodes.append({
    "id": nid("merge-csv"),
    "name": "Merge CSV Reads",
    "type": "n8n-nodes-base.merge",
    "typeVersion": 3,
    "position": pos(3, 1),
    "parameters": {"mode": "append", "numberInputs": len(csv_paths)},
})

# 11. Build Context Summary
context_code = '''/**
 * Build a compact context summary for the Master Planner.
 *
 * The planner does not need the raw 180 sales rows -- that would blow the
 * context budget. We extract the headline numbers and the SKUs already
 * past or near reorder so the planner can pick the right subgoal first.
 *
 * Inputs reach this node via cross-node references to the four CSV-parse
 * nodes upstream. We do NOT mutate them, only summarize.
 */
const inventory = $('Read Inventory JSON').all().map(i => i.json);
const sales     = $('Read Sales JSON').all().map(i => i.json);
const suppliers = $('Read Suppliers JSON').all().map(i => i.json);
const goal      = $('Set Goal').first().json.goal;

const stockout_risk = inventory
  .filter(r => Number(r.on_hand) <= Number(r.reorder_point))
  .map(r => ({ sku: r.sku, name: r.name,
               on_hand: Number(r.on_hand),
               reorder_point: Number(r.reorder_point) }));

const overstock_risk = inventory
  .filter(r => Number(r.on_hand) > Number(r.reorder_point) * 5)
  .map(r => ({ sku: r.sku, name: r.name,
               on_hand: Number(r.on_hand),
               reorder_point: Number(r.reorder_point) }));

const supplier_summary = suppliers.map(s => ({
  supplier_id: s.supplier_id,
  on_time_rate: Number(s.on_time_rate),
  defect_rate: Number(s.defect_rate),
}));

return [{
  json: {
    goal,
    context_summary: {
      sku_count: inventory.length,
      sales_rows: sales.length,
      stockout_risk,
      overstock_risk,
      supplier_summary,
    },
  },
}];
'''
nodes.append(code_node("Build Context Summary", "build-context", context_code, 4, 1))

# 12. Master Planner LLM
nodes.append(http_anthropic(
    "Master Planner Agent", "master-planner", MASTER_PLANNER_SYSTEM,
    "'GOAL: ' + $json.goal + '\\n\\nCONTEXT:\\n' + JSON.stringify($json.context_summary, null, 2)",
    5, 1,
))

# 13. Parse Plan
parse_plan_code = '''/**
 * Extract the Master Planner's JSON from the Anthropic response envelope.
 * Anthropic returns { content: [{ type: "text", text: "..." }], ... }.
 *
 * If your planner replies with markdown fences (```json ...```), the
 * JSON.parse below will fail. Forbid fences in your system prompt
 * (preferred) or strip them here.
 */
const raw = $json.content[0].text.trim();
let plan;
try {
  plan = JSON.parse(raw);
} catch (e) {
  // n8n builds the error headline from line 1 only and splits it at every
  // colon (a trailing one gives "Unknown error"), so line 1 stays colon-free.
  throw new Error("Planner did not return valid JSON. See the Master Planner Agent output for the raw reply." +
    "\\nReply (first 500 chars):\\n" + raw.slice(0, 500));
}

// Pull the goal+context through so downstream branches can reference them.
const ctx = $('Build Context Summary').first().json;

return [{ json: { ...plan, _goal: ctx.goal, _context: ctx.context_summary } }];
'''
nodes.append(code_node("Parse Plan", "parse-plan", parse_plan_code, 6, 1))

# 14. Switch on next_subgoal
nodes.append({
    "id": nid("switch"),
    "name": "Route on Subgoal",
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.2,
    "position": pos(7, 1),
    "parameters": {
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "typeValidation": "strict"},
                        "conditions": [{
                            "leftValue": "={{ $json.next_subgoal }}",
                            "rightValue": label,
                            "operator": {"type": "string", "operation": "equals"},
                        }],
                        "combinator": "and",
                    },
                    "renameOutput": True,
                    "outputKey": label,
                }
                for label in ["forecast", "inventory", "supplier", "logistics"]
            ]
        },
        "options": {"fallbackOutput": "extra"},
    },
})

# 15. Forecast branch
nodes.append(code_node("Demand Forecast Engine", "demand-forecast",
                       js("demand-forecast.js"), 8, 0))
nodes.append(http_anthropic(
    "Forecast Context Adjuster", "forecast-adjuster", FORECAST_ADJUSTER_SYSTEM,
    "'Forecast row:\\n' + JSON.stringify($json, null, 2)",
    9, 0,
))

# 16. Inventory branch
nodes.append(code_node("Inventory EOQ Planner", "eoq",
                       js("eoq-optimizer.js"), 8, 1))
nodes.append(http_anthropic(
    "Inventory Exception Handler", "inventory-exception", INVENTORY_EXCEPTION_SYSTEM,
    "'Flagged SKU:\\n' + JSON.stringify($json, null, 2)",
    9, 1,
))

# 17. Supplier branch
nodes.append(http_anthropic(
    "Supplier Performance Monitor", "supplier-score", SUPPLIER_SCORE_SYSTEM,
    "'Supplier roster:\\n' + JSON.stringify($('Read Suppliers JSON').all().map(i => i.json), null, 2)",
    8, 2,
))

# 18. Logistics branch
build_requests_code = '''/**
 * Manufacture three illustrative shipping requests so the logistics branch
 * has work to do. In a real system these would come from order management;
 * we synthesize them here so the assignment is self-contained.
 *
 * One item per request, so the Logistics Coordinator (LLM) runs once per
 * request. The carrier catalogue is not emitted as items: the LLM prompt and
 * the Classical Logistics Fallback read it from "Read Shipping JSON" by name.
 */
const requests = [
  { type: "request", request_id: "REQ-001", weight_kg:  850, origin_region: "Asia",          dest_region: "North America", deadline_days: 14, perishable: false },
  { type: "request", request_id: "REQ-002", weight_kg:   60, origin_region: "North America", dest_region: "North America", deadline_days:  3, perishable: true  },
  { type: "request", request_id: "REQ-003", weight_kg: 1200, origin_region: "Europe",        dest_region: "North America", deadline_days: 21, perishable: false },
];
return requests.map(x => ({ json: x }));
'''
nodes.append(code_node("Build Shipping Requests", "build-requests", build_requests_code, 8, 3))
nodes.append(http_anthropic(
    "Logistics Coordinator (LLM)", "logistics", LOGISTICS_SYSTEM,
    "'Request:\\n' + JSON.stringify($json, null, 2) + '\\n\\nOptions:\\n' + JSON.stringify($('Read Shipping JSON').all().map(i => i.json), null, 2)",
    9, 3,
))
parse_logistics_code = '''/**
 * Extract the Logistics Coordinator's JSON decision from each Anthropic
 * response envelope ({ content: [{ type: "text", text: "..." }] }) so the
 * IF node downstream can route on `use_classical_fallback`.
 *
 * One item per shipping request. Each output item is the original request
 * from "Build Shipping Requests" plus the LLM's decision, so the Classical
 * Logistics Fallback receives the request it has to solve. Only a JSON
 * boolean `true` routes to the fallback; a non-boolean value (e.g. the
 * string "true") throws rather than silently taking the LLM path.
 *
 * A reply wrapped in an array is accepted: a one-element array is unwrapped,
 * and from several decisions the one with this item's request_id is used.
 */
return $input.all().map((item, i) => {
  const raw = item.json.content[0].text.trim()
    .replace(/^```(?:json)?\\s*/i, "")
    .replace(/\\s*```$/, "");
  let decision;
  try {
    decision = JSON.parse(raw);
  } catch (e) {
    // n8n builds the error headline from line 1 only and splits it at every
    // colon (a trailing one gives "Unknown error"), so keep line 1 of every
    // error in this node colon-free.
    throw new Error("Logistics Coordinator did not return valid JSON. See the Logistics Coordinator (LLM) output for the raw reply." +
      "\\nReply (first 500 chars):\\n" + raw.slice(0, 500));
  }
  const request = $('Build Shipping Requests').itemMatching(i).json;
  const id = request.request_id;
  if (Array.isArray(decision)) {
    decision = decision.length === 1 ? decision[0] : decision.find(d => d && d.request_id === id);
  }
  if (!decision || typeof decision !== "object" || Array.isArray(decision)) {
    throw new Error("Logistics Coordinator returned no decision object for " + id + ". See the Logistics Coordinator (LLM) output for the raw reply." +
      "\\nReply (first 500 chars):\\n" + raw.slice(0, 500));
  }
  const flag = decision.use_classical_fallback;
  if (flag !== undefined && typeof flag !== "boolean") {
    throw new Error("Logistics Coordinator returned use_classical_fallback = " + JSON.stringify(flag) +
      " (" + typeof flag + ") for " + id + ". It must be a JSON boolean (true or false).");
  }
  return {
    json: {
      ...request,
      llm_decision: decision,
      use_classical_fallback: flag === true,
    },
    pairedItem: { item: i },
  };
});
'''
nodes.append(code_node("Parse Logistics Decision", "parse-logistics", parse_logistics_code, 10, 3))
nodes.append({
    "id": nid("if-classical"),
    "name": "Use Classical Fallback?",
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.2,
    "position": pos(11, 3),
    "parameters": {
        "conditions": {
            "options": {"caseSensitive": True, "typeValidation": "strict"},
            "conditions": [{
                "leftValue": "={{ $json.use_classical_fallback }}",
                "rightValue": True,
                "operator": {"type": "boolean", "operation": "true"},
            }],
            "combinator": "and",
        },
        "options": {},
    },
})
nodes.append(code_node("Classical Logistics Fallback", "classical-logistics",
                       js("classical-logistics.js"), 12, 4))

# 19. Final Merge
nodes.append({
    "id": nid("merge-final"),
    "name": "Merge Subgoal Results",
    "type": "n8n-nodes-base.merge",
    "typeVersion": 3,
    "position": pos(13, 1),
    "parameters": {"mode": "append"},
})

# 20. Final Output
final_code = '''/**
 * Aggregate the active subgoal's output into a final business-friendly summary.
 * Only one branch fires per execution (the Switch routes on next_subgoal).
 *
 * TODO [medium] -- LO-1: closing the planning loop
 *   Decide what shape the human-readable summary should take. Suggested:
 *     { plan_id, executed_subgoal, key_findings: [...], next_recommended_subgoal }
 *   The `next_recommended_subgoal` is your hook for an iterative HTN -- feed
 *   it back into the planner on the next run to advance the plan.
 */
const items = $input.all().map(i => i.json);
return [{ json: { executed_subgoal: "TODO", raw_outputs: items } }];
'''
nodes.append(code_node("Final Output", "final-output", final_code, 14, 1))

# ---- Connections ----------------------------------------------------------

connections = {}


def connect(src, dst, src_index=0, dst_index=0):
    if src not in connections:
        connections[src] = {"main": []}
    while len(connections[src]["main"]) <= src_index:
        connections[src]["main"].append([])
    connections[src]["main"][src_index].append(
        {"node": dst, "type": "main", "index": dst_index}
    )


# Trigger -> Goal -> file reads
connect("Manual Trigger", "Set Goal")
for i, (label, _, _) in enumerate(csv_paths):
    connect("Set Goal", f"Read {label} File")
    connect(f"Read {label} File", f"Read {label} JSON")
    connect(f"Read {label} JSON", "Merge CSV Reads", dst_index=i)
connect("Merge CSV Reads", "Build Context Summary")

# Plan
connect("Build Context Summary", "Master Planner Agent")
connect("Master Planner Agent", "Parse Plan")
connect("Parse Plan", "Route on Subgoal")

# Switch outputs (index order = rule order: forecast, inventory, supplier, logistics)
connect("Route on Subgoal", "Demand Forecast Engine", src_index=0)
connect("Route on Subgoal", "Inventory EOQ Planner", src_index=1)
connect("Route on Subgoal", "Supplier Performance Monitor", src_index=2)
connect("Route on Subgoal", "Build Shipping Requests", src_index=3)

# Branch tails -> Final Merge
connect("Demand Forecast Engine", "Forecast Context Adjuster")
connect("Forecast Context Adjuster", "Merge Subgoal Results")
connect("Inventory EOQ Planner", "Inventory Exception Handler")
connect("Inventory Exception Handler", "Merge Subgoal Results")
connect("Supplier Performance Monitor", "Merge Subgoal Results")
connect("Build Shipping Requests", "Logistics Coordinator (LLM)")
connect("Logistics Coordinator (LLM)", "Parse Logistics Decision")
connect("Parse Logistics Decision", "Use Classical Fallback?")
connect("Use Classical Fallback?", "Classical Logistics Fallback", src_index=0)  # true
connect("Use Classical Fallback?", "Merge Subgoal Results", src_index=1)         # false
# The fallback feeds Merge input 1, not input 0: two parents on one input make
# n8n run Merge (and Final Output) once per parent when requests are split
# between the two paths. On separate inputs Merge waits and runs once.
connect("Classical Logistics Fallback", "Merge Subgoal Results", dst_index=1)

connect("Merge Subgoal Results", "Final Output")

# ---- Workflow envelope ----------------------------------------------------

workflow = {
    "id": "supply-chain-manager-v1",
    "name": "Supply Chain Manager (Starter)",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
    "pinData": {},
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(workflow, indent=2))
print(f"wrote {OUT}")
print(f"  nodes: {len(nodes)}")
print(f"  connection groups: {sum(len(v['main']) for v in connections.values())}")
