/**
 * Demand Forecasting Engine — classical statistical forecast.
 *
 * Pedagogical purpose
 * -------------------
 * This Code node implements the *classical* half of a hybrid planning
 * pipeline. It produces a deterministic, reproducible numeric forecast
 * for each SKU using:
 *   1. A 3-month moving average over recent demand
 *   2. A 12-month seasonal index that adjusts for cyclical patterns
 *
 * The downstream LLM node ("Forecast Context Adjuster") will take these
 * numbers and revise them using context the math cannot see — promotions,
 * news events, weather, viral product mentions. That handoff is the whole
 * point of the lesson: classical statistics for what is computable,
 * LLM reasoning for what is contextual.
 *
 * If your forecast looks suspicious (e.g. SKU-007 Wool Gloves projects
 * its low summer baseline forward), you have correctly built a *naive*
 * forecaster. The next node is supposed to catch what you missed.
 *
 * Reading: docs/planning-primer.md §"Classical vs LLM-based planning"
 */

// ---- Input contract -------------------------------------------------------
// This node's direct input is the Master Planner's plan item (via the Switch),
// so the sales rows are read by node name from "Read Sales JSON" (the parsed
// sales_history.csv): each row = {month, sku, name, units_sold}.
// CSV values arrive as strings, so units_sold is converted to a number here.
const sales = $('Read Sales JSON').all()
  .map(i => ({ ...i.json, units_sold: Number(i.json.units_sold) }));

// ---- Helpers (provided — do not change) -----------------------------------

function groupBySku(rows) {
  const out = {};
  for (const r of rows) {
    (out[r.sku] = out[r.sku] || []).push(r);
  }
  // Sort each SKU's series chronologically so "last 3" really means "most recent."
  for (const sku of Object.keys(out)) {
    out[sku].sort((a, b) => a.month.localeCompare(b.month));
  }
  return out;
}

function nextMonth(monthStr) {
  // "2025-12" -> "2026-01"
  const [y, m] = monthStr.split("-").map(Number);
  const d = new Date(Date.UTC(y, m, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

// ---- The two algorithms YOU implement -------------------------------------

/**
 * Compute a simple 3-month moving average over the most recent units_sold values.
 *
 * @param {Array<{units_sold: number}>} series  Full sorted series for one SKU.
 * @returns {number}  Mean of the last 3 months. If fewer than 3 months of
 *                    data exist, take the mean of what's available.
 *                    Empty series -> 0.
 *
 * Why this matters: the moving average is the simplest possible "trend"
 * estimator. It's a STRIPS-style assumption: we assume the recent past
 * predicts the near future. This breaks for viral products and discontinued
 * items — which is exactly why the seasonal index and the LLM step exist.
 */
function movingAverage(series) {
  // TODO [easy] — LO-3: classical baseline forecasting
  //   1. Slice the last up-to-3 entries from `series`.
  //   2. Sum their `units_sold` and divide by the count.
  //   3. Return 0 for an empty series.
  throw new Error("TODO [easy]: implement movingAverage()");
}

/**
 * Seasonal index for a target forecast month.
 *
 * Definition for month M:
 *   index(M) = mean(units_sold across rows where month-of-year == M)
 *              / mean(units_sold across the entire series)
 *
 * Interpretation: 1.0 = "average month", 1.5 = "this month historically runs
 * 50% above average", 0.4 = "this month historically runs 60% below average."
 *
 * With only 12 months of history, the per-month mean degenerates to the
 * single observation we have for that month. That's a known weakness — we
 * accept it for this exercise. Production seasonality models use 2+ years.
 *
 * @param {Array<{month: string, units_sold: number}>} series
 * @param {string} targetMonth  e.g. "2026-01" — only the "01" portion matters.
 * @returns {number}            Multiplier. Default to 1.0 if you can't compute one.
 */
function seasonalIndex(series, targetMonth) {
  // TODO [medium] — LO-3: time-series decomposition
  //   1. Extract the month-of-year part: targetMonth.split("-")[1] -> "01".."12"
  //   2. Compute monthMean = mean of units_sold in `series` where the month
  //      portion of row.month matches.
  //   3. Compute overallMean = mean of units_sold across the entire series.
  //   4. Return monthMean / overallMean. Guard against division by zero
  //      (return 1.0 if overallMean is 0).
  //   5. If no rows match the target month part, return 1.0.
  throw new Error("TODO [medium]: implement seasonalIndex()");
}

// ---- Main loop (provided) -------------------------------------------------

const bySku = groupBySku(sales);
const results = [];

for (const sku of Object.keys(bySku)) {
  const series = bySku[sku];
  const last = series[series.length - 1].month;
  const target = nextMonth(last);

  // Classical forecast = trend (moving average) × seasonality
  const ma = movingAverage(series);
  const si = seasonalIndex(series, target);
  const forecast = ma * si;

  // Crude statistical confidence — coefficient of variation, inverted.
  // The downstream LLM is supposed to revise this when context demands it.
  // Watch how often statistical confidence and contextual confidence diverge.
  const variance = series.length > 1
    ? series.reduce((acc, r) => acc + Math.pow(r.units_sold - ma, 2), 0) / series.length
    : 0;
  const cv = ma > 0 ? Math.sqrt(variance) / ma : 1;
  const confidence = Math.max(0, Math.min(1, 1 - cv));

  results.push({
    sku,
    name: series[0].name,
    target_month: target,
    forecast_units: Math.round(forecast),
    moving_avg: Math.round(ma * 10) / 10,
    seasonal_index: Math.round(si * 100) / 100,
    statistical_confidence: Math.round(confidence * 100) / 100,
    method: "moving_avg_3 × seasonal_index",
    notes: [],
  });
}

// n8n Code-node return contract: array of {json: ...}
return results.map(r => ({ json: r }));
