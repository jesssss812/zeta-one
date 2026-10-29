# Zeta One

**Trust and risk checks for AI agents that move money.**

> Autonomy without instability.

Businesses are starting to let AI agents pay their bills. A known agent with valid permissions can
still be manipulated: an invoice can carry instructions, and a vendor's bank details can be swapped.
Before a financial platform carries out an agent's payment, Zeta One answers three separate
questions and returns **allow**, **challenge** or **block**, with an evidence record saying why.

| | Question | How it is answered |
| --- | --- | --- |
| **Verify the actor** | Who is acting, and for which business? | The agent signs each request (Ed25519); unknown or revoked agents are blocked |
| **Bound its authority** | Did the business authorize this payment? | Scope, limits, expiry and revocation, checked in code |
| **Assess the action** | Is it fraud anyway? | Deterministic risk rules on the payment's context; a model reviews only the uncertain cases |

Built for the AITX & MLOps World Community Hackathon (Austin Tech Week, October 2026), Rho fintech
track, on Rho's API. It is not a Rho product. **Payment execution is simulated.**

## How a decision is made

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/decision-flow-dark.svg">
  <img src="docs/images/decision-flow-light.svg" width="900" alt="How a decision is made. A signed payment proposal is checked in code for identity (an unknown, revoked or badly signed agent is blocked), then authorization (anything outside the grant is blocked), then tier-0 risk rules on the vendor's records. A clear case goes straight to the policy; an uncertain case below a high floor goes to a model, which may lower soft signals but never a hard flag. The policy returns block, allow (payment simulated) or challenge (held for a person), each with an evidence record. In the feedback loop, a person records what turned out to be true and how it was verified, after a challenge or after a case review assistant gathers the evidence for a disputed payment. A verified finding becomes an append-only risk adjustment that the next payment to that account cites, and an evaluation case; a claim alone changes nothing.">
</picture>

Blue runs in code, purple is a model, pink is a person and grey is an input or a record; green,
amber and red are allow, challenge and block. Solid arrows are the decision, dashed arrows the
feedback loop. Which model reviews depends on the configuration: Claude Opus 5.5 by default, Jev
first in the `jev` configuration, or an open-weight model in Opus's place.

**What makes it different**

- **No model can talk a payment past a hard check.** Identity, authorization and hard risk flags
  are deterministic floors. A model may only lower soft signals, and each lowering is recorded.
- **Routine payments need no model.** A payment reaches a model only when tier 0, the deterministic
  risk rules, finds something to question and has not already set a high floor. The evaluation
  reports how often that happened and the cost per 1,000 decisions, next to fraud caught and honest
  payments stopped, for rules alone, Jev, an open-weight model and Claude Opus. Under `engineered`,
  59 of the 100 `test` cases reached a model, on a set built mostly from flagged cases; how often it
  would happen on a real business's payments is not measured.
- **The loop closes, and it is audited.** A finding of fraud that a person verified blocks that bank
  account for the business; a bank change that a person confirmed stops being a hard flag, so a
  model may clear it. A customer's report alone changes nothing. Each change is an append-only
  record the next decision cites. "Verified" means a person with the admin token recorded the
  finding with one of four recognised methods, such as a call-back on a number already on file;
  the gateway keeps that statement and who made it, and does not check the call-back itself.
- **Agents help people, not instead of them.** When a customer disputes a payment, an assistant
  gathers the internal records, researches the vendor on the web and links every point to its
  source. It has no verdict field; a person decides.

## What runs today

| Part | State |
| --- | --- |
| Gateway: identity, authorization, risk rules, policy, evidence, simulated payments | Working end to end over HTTP, on synthetic data in Rho's shapes |
| Model review: Claude Opus 5.5; Jev (OpenRouter, TypeSafe as backup); an open-weight model, Qwen 3.6 27B, on a GPU we rent | Each ran once on the full evaluation |
| Feedback loop: verified outcomes and risk adjustments | Working; recorded end to end in `site/data/loop.json` |
| Case review page with source links and a local chat model | Research and assembly ran live; the chat needs a local model |
| Evaluation: labelled `dev` and `test` sets and a `hard` set written outside the generator, seven configurations, cost table ([how it works](docs/reference/evaluation-system.md)) | Scored, one run each: [the report](data/eval/report.md) |
| Rho | Read-only: the API cannot make payments, so execution is simulated |

## Results

One run of each configuration on synthetic cases, on 29 October 2026, so none of these is a
production rate. "Acceptable" means the decision matched the case's label or one of its listed
alternatives; "stopped" means challenged or blocked.

| Configuration | `test`: acceptable, of 100 | `test`: fraud let through, of 49 | `test`: honest payments stopped, of 51 | `hard`: acceptable, of 12 | `hard`: fraud let through, of 6 | $ per 1,000 decisions on `test` |
| --- | --- | --- | --- | --- | --- | --- |
| `rules`: tier 0 alone | 79 | 0 | 39 | 6 | 2 | 0 |
| `jev`: tier 0, then Jev, then Opus where Jev escalates | 90 | 2 | 14 | 7 | 2 | 12.00 |
| `engineered`: tier 0, then Opus where needed | 91 | 1 | 16 | 8 | 2 | 15.15 |
| `open_weight`: tier 0, then Qwen 3.6 27B on our GPU where needed | 94 | 0 | 19 | 7 | 2 | 1.85, GPU time |
| `strong`: Opus on every payment | 90 | 2 | 14 | 10 | 0 | 23.77 |

- **The rules alone let no generated fraud through, and stop 39 of 51 honest payments.** What the
  models add on `test` is clearing honest payments: down to 14–19 stopped.
- **Opus cleared fraud twice.** It took recent payments to the vendor as proof that an old,
  unconfirmed bank change was safe, though none of them was linked to the new account.
- **The open-weight model scored highest on `test`**, at about an eighth of the cost of Opus where
  needed. Its prompt has a section written from its own `dev` errors, which Opus's prompt does not,
  and on `hard` it scored 7 of 12 against 10 for Opus on every payment.
- **The rules' blind spot shows on `hard`.** Two detectable frauds there trip no tier-0 rule, so
  every configuration that escalates only uncertain cases allowed them without asking a model; Opus
  on every payment caught both.
- **A defect the evaluation found:** once a model rates a payment high, the policy treats an amount
  that differs from the bill as a redirect and blocks it, where two authorization cases require a
  challenge. It is not fixed.

What the numbers cannot show:

- `hard` has 14 cases written outside the generator; 12 are scored. The other two are frauds no
  configuration can see from the evidence, and every configuration but always-challenge allowed
  them. At this size an interval spans about ±25 points, and the open-weight arm ran on `hard` under
  a newer policy version than the others (they differ on one case).
- Generated `dev` and `test` cases share one structure (steady monthly payments, a few synthetic
  banks), the generator's dimensions resemble tier 0's own features, and 15 `test` combinations
  also appear in `dev`. `test` measures overfitting to the tuning within that structure, not
  behaviour on unlike cases.
- The labels are weakly checked. A person labelled 40 `test` cases blind; the AI labeller agreed on
  45%, chance level (Cohen's κ −0.01). After reading the AI's reasons, the person took its label on
  15 of the 22 disagreements and kept their own on 7. The other 60 labels, all 35 routine cases
  among them, are the AI labeller's alone.
- Opus's cost uses cache reads at 0.1× the input price, where Anthropic bills 0.05×, so it is
  slightly high. The open-weight cost is the rented GPU's hourly rent ($0.59) for each call's time,
  an upper bound; a business running its own GPU pays a fixed cost whatever the volume.

The [report](data/eval/report.md) has the intervals, the per-category rates, the baselines and the
limits.

## Quick start

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
cp .env.example .env                 # keys are optional; see below
python3 scripts/check.py             # compile, secret, link and docs checks, then the tests
.venv/bin/python scripts/keygen.py   # once: the demo agent's signing key
.venv/bin/uvicorn zeta_one.gateway.app:app --port 8000
```

For the whole story on one screen (a payment, a fraud report, a verified finding, what changes
next), run the demo on its own sandbox and open `http://127.0.0.1:8001/demo`:

```bash
.venv/bin/uvicorn zeta_one.demo.app:app --port 8001
```

Each step can open its evidence on the review page. Models are off unless it is started with
`ZETA_DEMO_LIVE=1`, which calls Claude for escalations and case files (paid).

Or, with the gateway running:

```bash
curl -s -X POST localhost:8000/v1/scenarios/vendor_payment_method_changed/run -H 'Content-Type: application/json' -d '{}'
```

Open `http://localhost:8000/review` for the case review page. It asks for `ZETA_ADMIN_TOKEN` from
`.env`.

Reproduce the recorded runs the site shows:

```bash
.venv/bin/python scripts/demo_loop.py      # the feedback loop, no model calls
.venv/bin/python scripts/record_runs.py    # scenario results and the evaluation report
```

**Environment** (`.env.example` lists every variable):

| Variable | Needed for |
| --- | --- |
| `ZETA_ADMIN_TOKEN` | Admin endpoints and the review page; `scripts/keygen.py` writes it to `.env` |
| `ANTHROPIC_API_KEY` | Claude model review and the case review assistant |
| `OPENROUTER_API_KEY`, `TYPESAFE_API_KEY` | Jev |
| `OPEN_WEIGHT_BASE_URL`, `OPEN_WEIGHT_MODEL`, `OPEN_WEIGHT_API_KEY`, `OPEN_WEIGHT_GPU_HOURLY` | The open-weight arm on its own GPU server |
| `CHAT_BASE_URL`, `CHAT_MODEL`, `CHAT_API_KEY` | The case chat: a local model by default (`ollama pull qwen2.5:7b`), or the open-weight arm's GPU server with its key, which sends the case to that server |
| `RHO_API_TOKEN` | The read-only Rho staging check (needs the hackathon VPN) |

With no keys, everything runs: escalated cases are held for a person and the tests use stubs.

## Tech stack

Python 3.13 or later (CI runs 3.14), FastAPI, Pydantic, SQLite, pytest and Hypothesis.

| Piece | What it is | How Zeta One reaches it |
| --- | --- | --- |
| [Claude Opus 5.5](https://www.anthropic.com/claude) | Anthropic's large language model; the strong risk tier | The Anthropic API |
| [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | TypeSafe's typed decision model (a "System One" model): it answers fixed questions with probabilities instead of writing text; the cheap risk tier ([details](docs/reference/jev.md)) | [OpenRouter](https://openrouter.ai), a service that routes one API to many model providers; TypeSafe's own API as the backup |
| [Qwen 3.6 27B](https://huggingface.co/Qwen/Qwen3.6-27B-FP8) | An open-weight model (weights published under Apache 2.0), compared in Opus's place | [vLLM](https://docs.vllm.ai), an open-source model server, on one GPU we rent |
| [Ollama](https://ollama.com) | Runs a small model locally | The case review page's chat, unless it is pointed at the GPU server above |

A static site is in `site/`. Where each piece runs is in
[docs/strategy/architecture.md](docs/strategy/architecture.md).

## Data

All data in this repository is synthetic. The seed (`data/seed/`) is generated by
`zeta_one/rho/seed.py` with a fixed random seed, in the shapes of Rho's API; its provenance is in
`data/seed/provenance.json`. Evaluation cases are generated from a fixed seed; Claude Haiku 5.5
writes their wording without seeing the labels, Claude Sonnet 5.5 labels them blind, and a person
checks a sample. The `hard` set is written outside the generator, drafted with Claude and approved by
a person. Raw Rho staging data never leaves the laptop. See
[docs/reference/staging-data.md](docs/reference/staging-data.md) and
[docs/strategy/evaluation.md](docs/strategy/evaluation.md).

## Limitations

- Synthetic results are not production accuracy.
- Protection covers only payments routed through the gateway; an agent that bypasses it is not
  checked.
- Authorization records are unsigned and the evidence store is editable by whoever runs the
  gateway.
- Bank-detail changes made before monitoring began may be invisible.
- Jev's probabilities are treated as uncalibrated until our cases can measure them.
- The evaluation is one run per configuration on small synthetic sets with weakly checked labels;
  its limits are listed under [Results](#results).
- "Verified" findings are a person's recorded statement of how they checked; the gateway does not
  confirm the check, and the admin token is shared rather than per person.

What is not done is in [docs/roadmap.md](docs/roadmap.md).

## Documentation

- [docs/strategy/product.md](docs/strategy/product.md): the problem, the decision model and scope.
- [docs/reference/evaluation-system.md](docs/reference/evaluation-system.md): how it is evaluated, and who does each step.
- [docs/reference/demo-api.md](docs/reference/demo-api.md): the HTTP API and the evidence record.
- [docs/README.md](docs/README.md): every document.
