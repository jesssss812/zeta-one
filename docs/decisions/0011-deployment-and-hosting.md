# 0011: Live on the laptop, SQLite state, recorded runs on a Vercel site, CI on every push

Date: 2026-10-27. Status: accepted. Amends 0005 (where the UI lives).

## Context

The judges reproduce the build from the README, score a live Hack Fair demo and a Loom, and accept
a screen capture in place of a deployed URL ([../reference/hackathon.md](../reference/hackathon.md)).
The live Rho read needs a VPN only the owner's laptop has. A public gateway would expose open demo
endpoints and a way to spend the owner's Anthropic budget ([../strategy/security.md](../strategy/security.md)).
Several coding agents will push to `main` at once. The hackathon offers $25 of Supabase credit. The
options and their tradeoffs are in [../strategy/architecture.md](../strategy/architecture.md).

## Decision

1. **The live gateway runs on the owner's laptop**, bound to 127.0.0.1, for the Loom and the Hack
   Fair. No hosted gateway in the first version.
2. **Gateway state is SQLite**, `data/zeta.db`. Module SQL stays plain, so a move to Postgres later
   is small.
3. **The strong tier calls the Anthropic API directly** with the owner's Console key.
4. **The submission site is static, deployed from `site/` to Vercel.** It shows **recorded results
   of real engine runs**: after the real engine runs, a script writes each scenario result and the
   evaluation report into `site/data/` in the demo API's shapes, dated and labelled as recorded.
   The gateway also serves an evidence view locally.
5. **GitHub Actions runs `scripts/check.py` on every push to `main`**, so the check holds for every
   agent, not only where the pre-push hook is enabled.

## Alternatives

- **A hosted gateway** (Render, Cloud Run, Fly.io, Vercel functions): a live deployed URL, at the
  cost of sleep or setup, non-persistent SQLite, and a public attack surface. Revisit after the core
  works, as a recorded-mode copy with no model calls and the admin endpoints off.
- **Supabase Postgres for state:** durable and hosted, but judges would need a project and keys to
  reproduce. It fits only alongside a hosted gateway; the credit would cover that.
- **GitHub Pages for the site:** needs a paid plan while the repo is private, so the URL would come
  only on submission day.

## Consequences

- The deployed URL shows the presentation and recorded real runs, never a live engine; the site says
  so.
- Judges without the VPN run everything except the live Rho read; without an Anthropic key, they can
  still read the recorded results.
- The Supabase and Apify credits go unused unless a hosted gateway is added later.
