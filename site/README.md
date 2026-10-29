# Zeta One submission site

Static, dependency-free presentation site with optional lightweight motion. No API calls, model runs, or payment actions.
The page explains the project and shows one labeled illustrative decision. Payment execution is
simulated throughout the project.

## Preview

From the repository root:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open http://localhost:4173. FastAPI can also serve this directory unchanged. All assets are relative.

## Content

- `index.html`: project story, the decision flow, synthetic decision example, engineering approach,
  the feedback loop, the evaluation summary with the main design trade-offs, and the demo video space. Replace the labeled video placeholder with an accessible video/embed once
  a recording exists; add a link to the actual app when it is ready.
- `evaluation.html`: how the evaluation works and who does each step (a person, a model, code), in
  the same colours as the flow in `docs/reference/evaluation-system.md`; change the two together.
- `fonts.html`: four wordmark studies for choosing the name and ζ typography; separate from the submission page.
- `zeta-mark.svg`: the existing zeta logo exported for the root README.
- `styles.css`: responsive presentation, keyboard focus, reduced-motion support, and decorative curve/background animation. The wave loops with a pause control and pauses offscreen; reduced-motion disables it.
- `motion.js`: one-time scroll reveals using IntersectionObserver and opacity/transform animations. Section 01 and supporting content reveal on entry; the compact example uses a native disclosure for evidence. content remains readable without JavaScript. Keyboard focus and reduced-motion preferences cancel reveals. No libraries, scroll listeners, or delayed content fetching.
- The decision example is drawn from the engine-owned
  [vendor payment-method change fixture](../data/fixtures/vendor_payment_method_changed.json).
  It is authored synthetic data, not a live engine result. No latency, savings, or accuracy figures
  are invented. The recorded live run of the same scenario in `site/data/scenarios/` gives the
  same challenge. Update the example if the canonical scenario changes.

The site prioritizes a fast, coherent presentation over an interactive demo. Engine decisions and
API integration remain in the actual application. The video area says its content is forthcoming;
the evaluation figures are copied by hand from `data/eval/report.md`, so change them when the report
changes. The decision flow under "Why this matters" and the feedback loop in section 04 match the
diagram in the root README (`docs/images/decision-flow-*.svg`); change them together.

Checks: `python3 scripts/check.py` from the repository root. Manually verify page anchors, desktop
and narrow layouts, visible focus, and absence of missing assets. Run `node --check site/motion.js` for JavaScript syntax. There is no frontend build step.

The root README and section 02 share five product principles: cost, security and private inference,
customer friction, evaluation methods, and human-controlled feedback. Keep their claims consistent.
Hosted and self-hosted data boundaries must remain explicit; OpenJev is a possibility, not a tested arm.

## Demo and fintech integration

The public section at `index.html#integration` distinguishes fresh decisions in the local demo
from this static website and a proposed platform integration. `integration-flow.svg` is the shared
diagram used here and in [the integration reference](../docs/reference/fintech-integration.md),
which owns the engineering details. Keep its implemented/demo and proposed/platform boundaries
consistent when updating the site. Live mode calls models only for eligible assessments; a fresh
decision does not imply a model call or live bank data.
