# Zeta One submission site

Static, dependency-free frontend. The decision engine owns decisions; this site renders the
[demo API contract](../docs/reference/demo-api.md). No Rho calls, keys, or decision logic live here.
Payment execution is simulated. The initial scenario is synthetic and illustrative, with no
model run or measured cost/latency.

## Preview

From the repository root:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open http://localhost:4173. Select **Decision engine** and run the scenario to call the local engine
at http://localhost:8000. When FastAPI serves this directory on its own origin, select that origin
in the engine URL field. Static assets use relative URLs; mount the whole directory, not just HTML.
Only same-origin or loopback engine URLs are accepted. Failed engine requests remain errors and
never silently fall back to fixtures. The engine must permit the frontend origin through CORS.

## Content and integration

- `index.html`: presentation, demo video space, and evaluation space. Replace the labeled video
  placeholder with an accessible video/embed once a recording exists. No video or benchmark is
  currently fabricated.
- `styles.css`: responsive layouts, keyboard focus, and reduced-motion support.
- `app.js`: fixture loading, explicit engine requests, evidence rendering, accessible stage tabs.
- `fixtures/vendor_payment_method_changed.json`: verbatim copy of the engine-owned fixture in
  `data/fixtures/`, authored synthetically to illustrate a vendor payment-method change. Sync it
  from the canonical fixture when the engine team changes it; do not edit the copy independently.

Checks: `node --check site/app.js` and `python3 scripts/check.py` from the repository root.
Manual checks: fixture reveal and replay, evidence disclosures/links, all three stage tabs via
keyboard, engine failure, narrow viewport, and integration with the running engine when available.

## Implementation scope

The unified site introduces the product and opens directly into one guided decision. A static
implementation matches the chosen FastAPI stack and avoids a frontend build dependency. A separate
marketing site plus separate app was considered but adds duplicated presentation and integration.
The first version intentionally focuses on one scenario; review workflows and additional scenarios
remain later work. Inference savings, review savings, and challenge reduction require evaluation.

All frontend changes are contained in `site/`. The root README and docs belong to the engine side.
Suggested root README addition: “Preview the submission site with
`python3 -m http.server 4173 --bind 127.0.0.1 --directory site`. The guided demo uses a labeled
synthetic fixture or the local decision engine. Payment execution is simulated.”
