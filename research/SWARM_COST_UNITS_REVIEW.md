# Adaption inference cost units: credits, not an inferred dollar conversion

Primary-source check on 7 November 2026, before the larger main collection.
No new inference, training, POST, account query or account change was made for
this review. No scientific outcomes, credentials, account identifiers or account
balances are reproduced.

## The documented rate unit is explicit

Adaption's official [hosted-model pricing page](https://docs.adaptionlabs.ai/inference-stacks/models/)
states: **“Prices are in credits per 1 million tokens.”** Its table labels the
input and output columns as credits. The applicable standard rates are:

| Hosted model | Input credits / million tokens | Output credits / million tokens |
|---|---:|---:|
| `gemma-4-26b-a4b-it` | 0.0765 | 0.255 |
| `gemma-4-31b-it` | 0.09 | 0.34 |
| `glm-53-flash` | 0.15 | 0.50 |
| `glm-5.2` | 1.40 | 4.40 |
| `qwen3.8-27b` | 0.039 | 1.25 |
| `qwen3.5-397b` | 0.55 | 3.50 |
| `deepseek-v4-flash` | 0.04444 | 0.13332 |

The same primary page lists separate cached-input discounts. A standard-rate
calculation is therefore a conservative cache-agnostic estimate when the
relevant input-token count includes cached tokens; it is not a cache-adjusted
invoice. A model's upstream provider pricing or model-card limits do not replace
Adaption's hosted rate schedule.

For input and output counts I and O, the project's standard-rate arithmetic is:

`estimated Adaption credits = (I × input_rate + O × output_rate) / 1,000,000`.

With a trustworthy cached-token count C and a verified applicable cache rate,
the corresponding split would be `((I−C) × input_rate + C × cached_rate +
O × output_rate) / 1,000,000`. This formula is explanatory; it does not amend a
frozen estimator or retrospectively reprice any observation. Missing usage must
retain its declared reservation rather than become zero.

## What the observed native cost does and does not establish

The root session reported that six previously retained neutral service receipts
include a numeric `usage.cost` matching the standard-rate estimate to floating
precision. This is useful arithmetic consistency evidence. No additional
response was generated, and no model answer was inspected for this memo.

The [official Responses creation reference](https://docs.adaptionlabs.ai/api/resources/responses/methods/create)
documents token counts and token-detail maps, but its displayed usage schema
does not describe a `cost` member or explicitly assign that member a unit. The
documented [model catalog](https://docs.adaptionlabs.ai/api/resources/models/methods/list)
describes available model identities; its displayed response schema supplies no
credit-to-currency conversion.

Thus the strong conclusion is **published token-rate estimates are denominated
in Adaption credits**. The narrower statement about `usage.cost` is that the
observed value is numerically consistent with those credit estimates. This
review did not find a separate primary contract defining that native field as
USD, a settled invoice amount, or an exchange rate. Keep the native value and
the independently calculated estimate distinguishable.

## Consequences for the collection budget

1. Label Adaption token-rate forecasts, reservations and native collection caps
   in **Adaption credits**. The current credit-denominated cap convention agrees
   with the published rates. Do not relabel those same numbers as USD.
2. Keep Adaption credits separate from provider costs quoted in USD and from
   subscription allowances. Do not add unlike units into a supposed dollar
   total. A cross-provider report should label each provider's unit explicitly.
3. Use the approved native-credit ceiling, remaining-credit checks, conservative
   in-flight reservations and existing stop rules. This source review does not
   authorize a larger ceiling or reset an old counter. Arithmetic agreement is
   not a reason to remove operational spending controls.
4. The [sprint sponsor announcement](https://apartresearch.com/sprints/swarm-alignment-2026#resources)
   describes a $500 platform-credit award. Comparing an award description with
   an account balance cannot identify a conversion: prior grants, subscriptions,
   adjustments and usage need not be known. **No 3:1 or other conversion is
   inferred.** No private balance is necessary to support the rate-unit finding.
5. Training remains a different service. As recorded in
   `SWARM_TRAINING_ACCESS.md`, readable AutoScientist metadata does not establish
   a training quote or award coverage. Do not transfer these inference rates or
   native-cost observations to training.

For final results, distinguish known token usage, unknown reservations,
provider-reported native cost, estimated credit consumption and reconciled
billing. The [official support route](https://docs.adaptionlabs.ai/resources/support/)
can clarify the undocumented native field or account-specific conversion if
required; no message was sent. No financial conversion, guarantee of remaining
allowance, or invoice reconciliation is claimed here.
