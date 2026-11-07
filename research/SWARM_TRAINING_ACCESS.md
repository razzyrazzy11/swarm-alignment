# AutoScientist training access: read verified, launch and price unverified

Checked **7 November 2026, 15:50:52 UTC**. One authenticated, documented
read-only GET returned HTTP 200 and sixteen training-model entries. No dataset
was uploaded, no POST/estimate/recommendation was requested, and no training,
inference or account change occurred. The saved key was used only in process
memory; credentials, balances, request headers and native identifiers are not
included here. No main-study outcomes were inspected.

## What is now established

The [official HTTP reference](https://docs.adaptionlabs.ai/api/resources/autoscientist/methods/list_models)
documents `GET https://api.prod.adaptionlabs.ai/api/v1/autoscientist/models`.
The [Python SDK reference](https://docs.adaptionlabs.ai/api/python/resources/autoscientist/methods/list_models)
identifies the same operation as `client.autoscientist.list_models()`. The
request used this exact route, bearer authentication and disabled redirects.
It did not query the deprecated alias or guess a billing endpoint.

The account's saved key can read this catalog. The response contained model IDs,
declared size/context labels, training methods/types and reasoning-training
flags. It contained **no price quotation or explicit entitlement/credit-coverage
fields**. Read access is not proof that the service permits this key to create a paid job,
that any particular model will launch, or that the sprint award funds it.

Selected smaller entries from this actual response:

| Returned model ID | Declared size | Methods | Training types | Reasoning-trace training |
|---|---:|---|---|---|
| `Qwen/Qwen3.5-2B` | 2B | SFT, DPO | LoRA, full | true |
| `Qwen/Qwen3.5-4B` | 4B | SFT, DPO | LoRA, full | true |
| `Qwen/Qwen3-4B-Base` | 4B | SFT, DPO | LoRA, full | true |
| `google/gemma-3-4b-pt` | 4B | SFT | LoRA, full | false |
| `Qwen/Qwen3.5-9B` | 9B | SFT, DPO | LoRA | false |

These are catalog capabilities, not tested kernels, memory requirements,
minimum-row guarantees or measured training quality. In particular,
`Qwen/Qwen3.5-2B` is the smallest declared size returned in this snapshot;
`Qwen/Qwen3.5-0.8B` was **not returned**. The earlier feasibility memo's 0.8B
example therefore remains a static planning possibility, not a currently
verified selectable model for this account.

The [supported-model page](https://docs.adaptionlabs.ai/autoscientist/supported-models/)
expressly makes the runtime list authoritative. Its static list also differs
from the response in some IDs/methods; for example the actual Gemma entry above
is `-pt`, not the planning table's `-it`. Do not silently substitute one for the
other. Any follow-up must pin its exact verified ID and then verify the resolved
run configuration. Context metadata does not establish the feasible training
sequence length for every method/hardware configuration.

## Price and award coverage remain unresolved

The [official MCP guide](https://docs.adaptionlabs.ai/tools/mcp) says AutoScientist
training can consume credits, and explicitly excludes its creation tool from
the estimate-enabled data tools. The [creation reference](https://docs.adaptionlabs.ai/api/resources/autoscientist/methods/create)
lists model/recipe/iteration controls and an optional discount voucher, but this
review found no training cost quote or monetary spending-cap field there. One
iteration limits the loop; it does not establish a dollar maximum. A
hyperparameter recommendation would not itself be a price quote and was not
called.

The [FAQ](https://docs.adaptionlabs.ai/resources/faq/) explains data-adaptation
credit estimates; it does not supply an account-specific AutoScientist quote.
No signed-in billing/training UI was inspected in this check. Thus UI-only
quotes or account entitlements are **unverified**, not asserted absent.

[The sprint sponsor description](https://apartresearch.com/sprints/swarm-alignment-2026#resources)
offers $500 in Adaption Platform credits and describes training/data products.
This announcement does not settle how an individual award is applied to a
particular training run, any exchange between internal product-credit units and
dollars, or the job's maximum charge. Neither the existing seven-model hosted
inference catalog nor this sixteen-model training catalog proves those terms.
No universal conversion or price guarantee is inferred.

## What remains necessary before a training experiment

First require the separately registered scientific trigger: a reproducible
sufficient-evidence error after simpler delivery/procedure controls. Then
freeze a new model-specific training/evaluation protocol with fresh source-level
splits. The current study and its held-out results remain unchanged.

Before launching, obtain an explicit applicable training quote/maximum and
confirmation that the award covers that run, together with training-create
permissions and a feasible download/serving route. Protect current collection
reservations. If those facts cannot be established, leave training unlaunched;
readable model metadata is useful progress, not a completed intervention.
The [official support page](https://docs.adaptionlabs.ai/resources/support/)
provides the clarification route. No message was sent to support.

Private reproducibility evidence is retained in
`runs/training-access-20261107/catalog-20261107T155052Z.json`, with the local
single-GET script in the same ignored directory. The JSON contains scrubbed full
response metadata for this one access check, not scientific outcomes. It must
not be committed wholesale. This memo supplements
`SWARM_MONITOR_TRAINING_FEASIBILITY.md`; it does not amend the frozen study or
authorize training.
