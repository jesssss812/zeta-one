# What Jev is

Compiled 2026-10-27 from search results quoting TypeSafe AI's own pages (the
[announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev),
[homepage](https://typesafe.ai/) and [docs](https://docs.typesafe.ai/introduction)); the planning
session could not open those pages directly. `jevai.net` is not the vendor. Prices and latency are
**vendor claims**; the request shape and rate limits are **unverified**: confirm on the first real
call, then correct this file.

## From TypeSafe's own material

- **Jev** is TypeSafe AI's first public model, in early access, in a class they call **System One
  models**. It gives up text generation entirely: a request carries a `state` string (the context)
  and typed questions, and each answer is a typed value with a **calibrated probability**, trained
  with what they call Reinforcement Learning for Calibrated Decisions. Their own framing: set
  thresholds for when software acts on its own and when it asks for review.
- Three question types: **choice** (one of N labels), **noul** (yes/no), **score** (an ordinal
  level against criteria).
- Current release **Jev 1.14** (October 14, 2026), served as `jev-latest`. *Jev-Omni* is a separate
  open-weights model.
- **Price:** **$0.042 per million input tokens, output free.** A decision over a few hundred tokens
  costs well under a hundredth of a cent.
- **Latency:** 70–500 ms end to end (vendor figure); ~0.09 s P50 on OpenRouter's listing. One
  independent benchmark measured 5–6× faster than an LLM at the median, with p95 under 500 ms.
- **Access:** an API key created in the TypeSafe console; a late-October update says no waitlist
  approval is needed although the homepage still shows a waitlist link. Rate limits are quoted
  differently by every secondary source; read them from the console.
- **Accuracy (community benchmarks, not ours):** ~94% on simple multi-class choices, ~79% when there
  are many options; a Jev-first cascade matched a frontier LLM on a spam task while sending one
  message in nine to the LLM, and lost 1.6 points on Banking77 for a 5.5× cost cut.

## Access (shapes disagree between sources; verify)

| Route | Endpoint | Model id | Auth |
| --- | --- | --- | --- |
| Direct | `POST https://api.typesafe.ai/v1/systemone` | `jev-latest` | TypeSafe API key; Python SDK `typesafe-ai`, call `client.system_one(state=..., questions={...})`, read `.choices`, `.scores`, `.nouls` |
| OpenRouter | `POST https://openrouter.ai/api/alpha/decisions` (not `/chat/completions`) | `typesafe/jev-1.14` | OpenRouter key |

The most consistent request body is `{"model": "jev-latest", "state": "...", "questions": {name:
{"type": "choice" | "score" | "noul", "instructions": "...", "criteria" | "options": ...}}}`. Two
sources differ on whether a choice takes `options` or `criteria` and whether a score takes
`min`/`max`. Resolve on the first call.

## What this means for Zeta One

- Jev fits the **cheap classifier tier** exactly: a typed `choice` for risk level, `noul`s for
  "does this document instruct an agent to change payment details" and "does the proposal match the
  bill", each with a confidence that gates escalation. See
  [../decisions/0007-risk-tiers.md](../decisions/0007-risk-tiers.md).
- Jev is a risk signal, never identity or authorization (AGENTS.md rules 7 and 9).
- There is no language-model stand-in for Jev (decision 0009).

## How Zeta One calls it

`zeta_one/risk/jev.py` is the cheap tier. It posts to OpenRouter's decisions endpoint with
`OPENROUTER_API_KEY` (model `typesafe/jev-1.14`), and to TypeSafe's direct route with
`TYPESAFE_API_KEY` (`jev-latest`) only when OpenRouter can't be reached: no key, a timeout, 408,
429 or a 5xx. A bad answer is not retried on the other route, which would re-roll the model
(decision 0010). OpenRouter comes first so one key serves Jev and the open-weight arm; the cost is
an alpha endpoint and one more processor that sees the invoice text. Each result names its
`route` and any `routes_tried`. The request carries a `state` that is the strong tier's rendering
(gateway facts, then untrusted text in bounded blocks), and four questions: `risk_level` (choice:
low / elevated / high), `document_targets_agent`, `proposal_matches_documents` and
`vendor_impersonation_signs` (nouls). The parser accepts the answer shapes the sources describe
(`answers`, `results`, or `choices` and `nouls` keyed by question; a value with a probability, or a
probability per option) and treats anything else as invalid output, which fails closed. Until the
first real call, run with `.venv/bin/python -m pytest tests/risk/test_jev.py --live-models`, these
shapes are unverified. The live gateway uses Jev when `ZETA_RISK_CONFIGURATION=jev`; the evaluation
has a `jev` arm. The escalation rule after Jev is in
[../decisions/0007-risk-tiers.md](../decisions/0007-risk-tiers.md), with thresholds 0.8 and 0.9
recorded in each decision's configuration.

## Sources

TypeSafe's [announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev),
[homepage](https://typesafe.ai/) and [quickstart](https://docs.typesafe.ai/introduction/quickstart),
as quoted in search results of 2026-10-27; [OpenRouter listing](https://openrouter.ai/typesafe/jev-1.14),
[unofficial System One guide](https://github.com/typesafe-docs/typesafeai),
[jev-measured benchmark](https://github.com/WallerChen/jev-measured),
[independent benchmark](https://medium.com/@pravvich/typesafes-jev-beyond-the-hype-an-independent-benchmark-8bdc1c99d000),
[OpenRouter explainer](https://openrouter.ai/blog/insights/what-is-jev/).
