# What Jev is

Found 2026-10-27 from web search, because the vendor's own pages (`jevai.net`, `docs.typesafe.ai`)
could not be fetched from the planning session. Everything below is **unverified against official
docs**: confirm the endpoint, request shape and price on the first real call, then correct this
file.

## Confirmed by several independent sources

- **Jev** is a "decision model" (TypeSafe AI calls the product line *System One*) that never
  generates free text. A request carries a `state` string (the context) and a set of typed
  questions; the answer to each question is a typed value with a confidence.
- Three question types: **choice** (one of N labels), **noul** (yes/no), **score** (an ordinal
  level against criteria).
- Current version is **Jev 1.14**; `jev-latest` is an alias to it. There is also an open-weights
  variant, *Jev-Omni*, which is a different model.
- **Price:** OpenRouter lists `typesafe/jev-1.14` at **$0.042 per million input tokens, output
  free**; the vendor site lists $0.084 per million. Either way a decision over a few hundred tokens
  costs well under a hundredth of a cent.
- **Latency:** ~0.09 s P50 on OpenRouter's listing; the vendor claims 70–500 ms. One independent
  benchmark measured 5–6× faster than an LLM at the median, with p95 under 500 ms.
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
- If an API key or a working call isn't in hand by the end of Tue Oct 28, the cheap tier falls back
  to Claude Haiku 5.5 behind the same interface. The evaluation reports whichever ran.

## Sources

Search results of 2026-10-27: [OpenRouter listing](https://openrouter.ai/typesafe/jev-1.14),
[jevai.net](https://jevai.net/), [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart),
[unofficial System One guide](https://github.com/typesafe-docs/typesafeai),
[jev-measured benchmark](https://github.com/WallerChen/jev-measured),
[independent benchmark](https://medium.com/@pravvich/typesafes-jev-beyond-the-hype-an-independent-benchmark-8bdc1c99d000),
[OpenRouter explainer](https://openrouter.ai/blog/insights/what-is-jev/).
