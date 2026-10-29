# 0018: The open-weight arm runs on a GPU we control, as a customer's own server would

Date: 2026-10-29. Status: accepted. Supersedes point 2 of 0014 for the evaluation; the rest of 0014
stands.

## Context

Decision 0014 reached the open-weight arm through OpenRouter, which ran Qwen3 235B on its own
servers. That answers "can a cheaper open model do the job", but not the question a fintech that
adopts the gateway will ask: can it run with no case data leaving servers it controls? A fintech
with that rule would serve an open model on its own GPU. The closest thing we can run is a GPU we
rent and control, serving official open weights through the same kind of server the fintech would
use.

A 16 GB laptop holds only a model of about 9B parameters. On a rented 24 GB card a 27B model fits
only as a third party's 4-bit copy, and vLLM's guide for gpt-oss lists only A100, Hopper and
Blackwell cards. A 48 GB card in RunPod's Secure Cloud costs less per hour than a 24 GB RTX 4090
there.

## Decision

1. For the evaluation, the open-weight model is Qwen 3.6 27B in Qwen's own FP8 weights
   (`Qwen/Qwen3.6-27B-FP8`, Apache 2.0), served by vLLM 0.32.0 on one 48 GB NVIDIA A40 in RunPod's
   Secure Cloud, at $0.59 an hour. The gateway reaches it through `OPEN_WEIGHT_BASE_URL`, as any
   OpenAI-compatible server.
2. The server refuses any request without its access key, which lives only in `.env` and the
   pod's secrets. Only synthetic evaluation cases are sent to it; Rho staging data never is. The pod
   is terminated after the evaluation.
3. The request enforces the answer's JSON schema while decoding and turns the model's thinking off.
4. Its cost is the GPU's hourly rent for each call's time (`OPEN_WEIGHT_GPU_HOURLY`), failed calls
   included. Calls that share the GPU are each charged in full, so the figure is an upper bound.

## Consequences

- The report sets Opus through Anthropic beside an open model on hardware a customer could run
  itself. The earlier `dev` run of Qwen3 235B through OpenRouter stays recorded as it was.
- A self-hosted model is a fixed cost: a GPU kept on all day costs the same at any volume. It costs
  less than per-token APIs only at high, steady volume, which is the adopter's case, not ours. The
  engine's main saving, that most payments never reach a model, holds wherever the model runs.
- A 27B model is expected to trail Opus. The run shows by how much, and in particular how much
  fraud it allows by lowering soft signals, which no model can do to tier 0's floors.
- A customer that wants the cheap tier on its own servers too could look at open models built like
  Jev, such as openjev (MIT licence). We have not evaluated one, and openjev's own page says it is
  not hardened against prompt injection.
- The pod's address is public; the access key is its only protection, and vLLM checks it only on
  the API paths, not on its health check.
