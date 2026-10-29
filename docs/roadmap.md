# Roadmap

What is not done, as of 2026-10-29. Remove a line when it is done. Items marked **owner** need the
owner's own time or accounts.

## Live models

- **Owner:** to use the case chat, run `ollama serve` and `ollama pull qwen2.5:7b` (about 4.7 GB).
- The first live case file reported its web research cut short after one query, with the limit set
  at five searches. Find out what counts against the limit with dynamic filtering (the response's
  server-tool usage), then set the limit.

## Evaluation

The plan is in [strategy/evaluation.md](strategy/evaluation.md). Every configuration has been scored
once on the deterministic cases, `dev`, the frozen `test` and the frozen `hard` set; the results are
in [data/eval/report.md](../data/eval/report.md). Not done:

- **A defect the scored run found:** once a model rates a payment high, the policy treats an amount
  that differs from its bill as a redirect and blocks it, where the deterministic authorization
  cases require a challenge. The model arms fail one or two of those cases.
- The other 6 `hard` specs need the business's own supporting records (5) or the lookalike vendor's
  record in the models' input (1) before they can be converted.
- Repeat runs with pass^3; an attacking model aimed at model lowering of soft signals; expected cost
  with the missed-fraud weight halved and doubled.
- Jev's calibration on our cases, and whether Opus would gain from the open-weight model's prompt
  section on confirmation records.

## Submission (by Thu Oct 29, 5:00 PM CT)

Checklist in [reference/hackathon.md](reference/hackathon.md).

- The site renders the recorded runs in `site/data/`.
- **Owner:** run `scripts/keygen.py` once on the demo machine, so the default gateway registers
  the demo agent and has an admin token.
- **Owner:** connect the repo to Vercel, serving `site/` as a static site (decision 0011).
- **Owner:** Loom video, 2–5 minutes; 150–300 word write-up; team roster; confirm the Rho
  fintech track.
- **Owner:** make the repo public, after checking it holds no personal details, raw staging data
  or credentials.

## Extensions

Live Rho read through a GET-only client; Jev's calibration on our cases; `renew_authorization` and
`verify_payee` challenge types with the friction score; extra tier-0 features; `notify`; observe
mode; a Claude Code hook refusing shell commands that touch `.env` or `*.ovpn`; testing Rho's MCP
connector in claude.ai and recording the answer in [reference/rho-api.md](reference/rho-api.md).

## After the hackathon

- Evaluation follow-ups in [strategy/evaluation.md](strategy/evaluation.md#after-the-hackathon).
- Security follow-ups in [strategy/security.md](strategy/security.md#later): snapshot comparison
  of payment methods, signed authorizations, hash-chained evidence, rate limits, key rotation.
- Approval side panel: poll Rho items waiting for approval and score them (decision 0003).
- For a customer that wants no case data to leave its servers: evaluate an open-weight model built like
  Jev, such as openjev, as a self-hosted cheap tier, including against prompt injection (decision 0018).
- Case review assistant: dual control on findings, a per-day model budget, and an evaluation of the
  assistant on adversarial web pages (decision 0015).
