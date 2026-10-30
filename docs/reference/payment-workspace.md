# Payment review workspace

The workspace at `/workspace/` presents an inbox of synthetic payments. Choose a scenario, inspect
its invoice and decision evidence, and review held payments. The explanatory site and workspace
share a visual identity; the original guided story remains available locally at `/demo-legacy`.
All payment execution is simulated.

## Public preview and local operation

| Environment | What runs | What the visitor can do |
| --- | --- | --- |
| Public static site | Prepared records from real deterministic engine runs; no gateway or model call | Browse examples, inspect evidence and select another prepared example |
| Local, default | A fresh signed proposal through the real identity, authorization, context, tier-0 and policy stages | Choose scenarios, record human findings and resolve holds against the sandbox |
| Local, `ZETA_DEMO_LIVE=1` | The same pipeline with models available for eligible risk assessments and explicitly requested case assembly. The risk tiers are the configuration `ZETA_RISK_CONFIGURATION` names: `engineered` (the rules, then Claude Opus where they leave a payment uncertain) by default, or `jev` (the rules, then Jev, then Opus where Jev escalates) | Exercise the working system with fresh model calls when the pipeline requires them |

A fresh decision does not necessarily involve a model. Stage results and timings show what ran.
Opening a payment's evidence does not assemble a case or invoke a model. **Assemble case** is an
explicit action. A human finding records what the reviewer says they verified; selecting a
verification method does not perform that verification for them.

Start the local workspace:

```bash
.venv/bin/uvicorn zeta_one.demo.app:app --port 8001
```

Open `http://127.0.0.1:8001/workspace/`. Models are disabled by default. The server is a local demo
with synthetic state, not a public multi-user service; keep it bound to loopback. Its demo routes
are not a production authentication boundary. Restarting or resetting discards sandbox state.

Preview the public version:

```bash
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open `http://127.0.0.1:4173/workspace/`. Public review actions that would need a gateway are disabled.
The public random-example control chooses among packaged records; it does not generate a new
model decision. These examples demonstrate behavior, not evaluation accuracy.

## Scenario provenance

Workspace recipes are synthetic demonstration data, separate from the frozen evaluation sets.
The export script records the deterministic engine's actual decisions for the public preview:

```bash
.venv/bin/python scripts/record_workspace.py
```

The public artifacts include provenance so a recorded result is distinguishable from a fresh
local assessment. No public request invokes the export script. See the
[demo API](demo-api.md) for the underlying gateway contracts and
[fintech integration reference](fintech-integration.md) for the engineering still required to
connect this decision engine to a real payment platform.
