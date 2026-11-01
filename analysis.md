# Assignment 3 Analysis
*Joseph Zaki*

### Algorithm Comparison

Examining the demand forecast for SKU-001, we see a moving average of 32.3 and a seasonal index of 0.31, giving us a forecast amount of 10 units for our classical baseline. The LLM revised forecast keeps the forecast at 10 with the following reasoning: "The classical forecast of 10 units is derived from a moving average of 32.3 multiplied by a seasonal index of 0.31, which is plausible for sunglasses in January — a low-demand winter month in the Northern Hemisphere." The model also notes that no additional contextual notes were provided, giving it no reason to revise the forecast.

I believe this is an issue with the Deman Forecast Engine code node because this engine always sets `"notes": []`, meaning no contextual notes are ever provided to the LLM. This led to the LLM opting not to revise any forecasts even for anomalous SKUs. I'm not sure where in the process these notes should be injected.

### EOQ Assumption Analysis

In the Inventory EOQ planner node, I implemented the `detectViolations()` method to check that the assumptions of the EOQ formula and attach any flags for violated assumption. This method checks the following flags:

1. `viral_spike`: This flag is triggered for any SKU where the mean traffic of the last three months is greater than 2.5 * the average traffic of the prior 9 months. This should trigger for any SKUs with substantial viral spikes, such as SKU-007. The downstream LLM handler recommends placing an order greater then EOQ to accomodate the spike in demand.
2. `declining`: This flag is triggered for any SKUs with heavily declining demand by checking that the mean demand over the last 3 months has fallen below half the demand for the first three months. An example of this is SKU-013. The LLM recommends not ordering at all to avoid overstocking the item and also recommends marking down the item in some cases to reduce holding costs.
3. `low_velocity`: This flag checks that the annual demand of this product is not too low (below 500 units). In the case of the products provided, none trigger this flag.
4. `long_lead_time`: This flag indicates that a SKU has a long lead time in production also checking if it is especially volatile since sudden demand spikes will be difficult to respond to due to the long lead time. SKUs SKU-005 and SKU-006 both trigger this flag. The threshold for this flag is a lead time greater than 28 days and a coefficient of variation greater than 0.5 since this indicates nearly a month of lead time for the product and fairly high variance in demand, putting these products at higher risk of delays in fulfilling orders. The LLM recommends ordering up to 50% more than EOQ's reccomended amount to avoid stock outs.

### Supplier Rubric Defense

When creating the weights for the supplier rubric, I decided on the following:

1. **Cost**: 40% - Cost should make up a significant component of the rubric to ensure the business stays profitable, Suppliers that are slightly better,faster, or more reliable but much more expensive likely are not worth it.
2. **Lead time**: 20% - Lead time is an important component, but none of the products in inventory require very urgent delivery. That being said, a supplier's lead time is not negligible and it may be worth paying a little bit more for a faster delivery, potentially avoiding a stock out and many missed sales.
3. **Quality**: 10% - Quality is an important metric, but all the given suppliers have fairly low defect rates, making this metric less consequential.
4. **Reliability**: 30% - Reliability is the second most important metric as frequent delays and unreliable fulfillment times undermines the entire workflow. Decisions are made assuming that inventory will be restocked when expected and frequent delays will lead to delayed responses to viral spikes and declines since we will need to place orders earlier than preferred.

### Run Metrics

**Forecast Path**:
- Latency: ~20s
- Tokens consumed: ~9,000 input tokens, ~ 3,600 output tokens
- Approximate cost: ~$0.14

**Inventory Path**:
- Latency: ~13s
- Tokens consumed: ~7,300 input tokens, ~ 1,700 output tokens
- Approximate cost: ~$0.08

**Supplier Path**:

- Latency: ~30s
- Tokens consumed: ~2,100 input tokens, ~ 2,000 output tokens
- Approximate cost: ~$0.06

**Logistics Path**:
- Latency: ~25s
- Tokens consumed: ~5,400 input tokens, ~2,100  output tokens
- Approximate cost: ~0.08$


### Primer Questions Reflection

Question 1: Where in your workflow does a classical algorithm produce a wrong answer that the LLM catches, and where does the LLM produce a wrong answer that the classical layer catches?

> In the inventory path of the workflow, the EOQ algorithm produces a classical approach to determining how much inventory to order. This classical approach fails to adjust when assumptions are violated, so the LLM Exception Handler adjusts the recommendation. In the logistics path, the LLM makes a a decision based on hard and soft constraints, but defers decision to the classical fallback in the case where no soft constraints are affecting the decision.

Question 2: If your Master Planner started emitting next_subgoal: "audit_warehouse" (a value the Switch doesn't know about), what would happen, and what change would you make to the workflow so that wasn't a silent failure?

> Currently, if the Master Planner emitted an unexpected subgoal, the workflow would stop at the Route on Subgoal node leading to a silent failure. This could be addressed by deciding what happens in the case of a fallback. We could direct the output back to the Master Planner or another LLM node telling it to try again and enure it selects one of the permitted subgoals. Alternatively, we could raise an alert and inform a human.

Question 3: Why does EOQ give a confident, wrong answer for SKU-013 (Wired Earbuds), and what flag in your detectViolations() should fire to keep that from going to production?

> EOQ gives a confident wrong answer for SKU-013 because the assumption that demand is roughly constant is violated, but the EOQ formula does not take this into account. For this SKU, the `detectViolations()` function should raise the `declining` flag.

Question 4: Why is supplier scoring an LLM job and EOQ a classical job? What would change if I asked you to swap them?

> Supplier is scoring an LLM job because in this case there are multiple trade offs to consider. There isn't necessarily a closed-form formula that can provide the ranking necessary for the suppliers, since this also needs to react to the incoming requests. EOQ on the other hand, is a closed form solution to determining how much inventory to order, making it well suited to a classical planning approach. If we were to swap these, it may be difficult for the LLM to produce well calibrated inventory order recommendations without a classical baseline to compare to or work off of. Additionally, applying a classical approach to comparing suppliers may result in less robust decision making since we would be reducing the amount of reasoning going into comparing the available suppliers with the incoming requests.

## Demo Video

https://youtu.be/jXHJkkR5B7A