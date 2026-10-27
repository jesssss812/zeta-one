"""The demo API (docs/reference/demo-api.md). Serves JSON to the site; holds no decision logic."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from zeta_one.contracts import POLICY_VERSION
from zeta_one.gateway import scenarios

app = FastAPI(title="Zeta One gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_decisions: dict[str, dict] = {}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.get("/v1/health")
def health() -> dict:
    return {"engine_version": None, "policy_version": POLICY_VERSION, "data_backend": "seed", "simulated": True}


@app.get("/v1/scenarios")
def list_scenarios() -> list[dict]:
    return scenarios.list_scenarios()


@app.post("/v1/scenarios/{name}/run")
def run_scenario(name: str):
    try:
        result = scenarios.run(name)
    except KeyError:
        return _error(404, "unknown_scenario", f"no scenario named {name}")
    body = scenarios.dump(result)
    _decisions[result.decision_record.decision_id] = body["decision_record"]
    return body


@app.get("/v1/decisions/{decision_id}")
def get_decision(decision_id: str):
    if decision_id not in _decisions:
        return _error(404, "unknown_decision", f"no decision {decision_id}")
    return _decisions[decision_id]


@app.get("/v1/eval/latest")
def eval_latest():
    return _error(404, "no_report", "no evaluation report yet")
