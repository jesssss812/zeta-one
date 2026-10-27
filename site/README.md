# Zeta One submission site

Static, dependency-free presentation site. No JavaScript, API calls, model runs, or payment actions.
The page explains the project and shows one labeled illustrative decision. Payment execution is
simulated throughout the project.

## Preview

From the repository root:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open http://localhost:4173. FastAPI can also serve this directory unchanged. All assets are relative.

## Content

- `index.html`: project story, synthetic decision example, engineering approach, evaluation space,
  and demo video space. Replace the labeled video placeholder with an accessible video/embed once
  a recording exists; add a link to the actual app when it is ready.
- `fonts.html`: four wordmark studies for choosing the name and ζ typography; separate from the submission page.
- `styles.css`: responsive presentation, keyboard focus, and reduced-motion support.
- The decision example is drawn from the engine-owned
  [vendor payment-method change fixture](../data/fixtures/vendor_payment_method_changed.json).
  It is authored synthetic data, not a live engine result. No latency, savings, or accuracy figures
  are invented. Update the example if the canonical scenario changes.

The site prioritizes a fast, coherent presentation over an interactive demo. Engine decisions and
API integration remain in the actual application. The video and evaluation areas explicitly show
that their content is forthcoming. The review assistant and learning loop are planned extensions.

Checks: `python3 scripts/check.py` from the repository root. Manually verify page anchors, desktop
and narrow layouts, visible focus, and absence of missing assets. There is no frontend build step.

All changes stay in `site/`; the engine owns the root README and docs. Suggested root README text:
“Preview the submission site with `python3 -m http.server 4173 --bind 127.0.0.1 --directory site`.
It includes a labeled synthetic decision example. Payment execution is simulated.”
