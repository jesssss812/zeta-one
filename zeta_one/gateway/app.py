"""The gateway's HTTP API (docs/reference/demo-api.md and the implementation plan's Gateway API).

Translates HTTP to and from the service; holds no decision logic. Run it on 127.0.0.1 only:
`python -m zeta_one.gateway.app`, or uvicorn without `--host`.
"""

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from zeta_one import db
from zeta_one.contracts import POLICY_VERSION, InvalidProposal, SignedRequest
from zeta_one.gateway import scenarios
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.service import EngineNotReady, Gateway
from zeta_one.gateway.wiring import engine_version, real_stages

HOST = "127.0.0.1"


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(gateway: Gateway) -> FastAPI:
    app = FastAPI(title="Zeta One gateway")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/v1/health")
    def health() -> dict:
        return {
            "engine_version": gateway.version,
            "policy_version": POLICY_VERSION,
            "data_backend": "seed",
            "simulated": True,
        }

    @app.post("/v1/actions/propose_payment")
    async def propose_payment(request: Request):
        signed = SignedRequest(
            method=request.method, path=request.url.path, headers=dict(request.headers), body=await request.body()
        )
        try:
            return await run_in_threadpool(gateway.propose, signed)
        except InvalidProposal as error:
            return _error(400, "invalid_proposal", str(error))
        except EngineNotReady as error:
            return _error(503, "engine_not_ready", str(error))

    @app.get("/v1/decisions")
    def list_decisions(limit: int = 50) -> list[dict]:
        return gateway.ledger.decisions(min(max(limit, 1), 500))

    @app.get("/v1/decisions/{decision_id}")
    def get_decision(decision_id: str):
        record = gateway.ledger.decision(decision_id)
        if record is None:
            return _error(404, "unknown_decision", f"no decision {decision_id}")
        return record

    @app.get("/v1/scenarios")
    def list_scenarios() -> list[dict]:
        return scenarios.list_scenarios()

    @app.post("/v1/scenarios/{name}/run")
    def run_scenario(name: str):
        try:
            result = scenarios.run(name)
        except KeyError:
            return _error(404, "unknown_scenario", f"no scenario named {name}")
        gateway.ledger.save_record(result.decision_record)
        return scenarios.dump(result)

    @app.get("/v1/eval/latest")
    def eval_latest():
        return _error(404, "no_report", "no evaluation report yet")

    return app


def default_gateway() -> Gateway:
    return Gateway(stages=real_stages(), ledger=Ledger(db.connect()), version=engine_version())


app = create_app(default_gateway())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=8000)
