# Zeta One

**Trust and risk checks for AI agents that move money.**

> Autonomy without instability.

Businesses are starting to let AI agents pay bills and move money for them. Before a financial
platform carries out an action from one of those agents, it needs to know three things: which agent
is acting and for whom, whether the business actually authorized this action, and whether the action
looks like fraud even if it is authorized. Zeta One answers those three questions for each proposed
action and returns **allow**, **challenge** or **block**, with an evidence record explaining why.

Built for the AITX & MLOps World Community Hackathon (Austin Tech Week, October 2026), Rho fintech
track, on Rho's API. It is not a Rho product.

## Status

The decision kernel, synthetic data store, signed-agent identity, authorization checks and
deterministic risk tier are implemented. Together they reproduce the five demo decisions in
local tests. Payment execution is **simulated**. The default HTTP gateway still needs these
stages wired in; see the [implemented interfaces and data provenance](docs/reference/deterministic-stages.md).

Run the checks locally:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
python3 scripts/check.py
```

The seed is synthetic and is not evidence of production fraud accuracy. Agents bypassing the
gateway are outside its protection. Authorization records are unsigned, evidence is editable,
and bank-detail changes before monitoring began may be invisible.

## Documentation

- [docs/strategy/product.md](docs/strategy/product.md): what Zeta One does and why.
- [docs/README.md](docs/README.md): all documentation.
