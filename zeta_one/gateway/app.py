"""The gateway's HTTP API (docs/reference/demo-api.md and the implementation plan's Gateway API).

Translates HTTP to and from the service; holds no decision logic. Run it on 127.0.0.1 only:
`python -m zeta_one.gateway.app`, or uvicorn without `--host`. The module-level `app` is built on
first access, so importing `create_app` opens no database and reads no `.env`.
"""

import base64
import binascii
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.exceptions import HTTPException

from zeta_one import db
from zeta_one.contracts import POLICY_VERSION, Authorization, Finding, InvalidProposal, SignedRequest, Verification
from zeta_one.gateway import admin, scenarios
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.reuse import RiskReuse
from zeta_one.gateway.service import EngineNotReady, Gateway, NotHeld, UnknownChallenge, UnknownDecision
from zeta_one.gateway.wiring import ROOT, configuration_from_env, engine_version, real_stages, register_demo_agents

HOST = "127.0.0.1"
EVAL_REPORT = ROOT / "data" / "eval" / "report.json"
REVIEW_PAGE = Path(__file__).resolve().parents[1] / "review" / "page.html"


class AgentRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1, max_length=128)
    business_id: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=200)
    public_key: str = Field(description="the Ed25519 public key, 32 raw bytes in base64")


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["approve", "reject"]
    by: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    # What the person established, and how (decision 0012); optional on a resolve.
    finding: Finding | None = None
    verification: Verification = "none"


class AdjustmentRevocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class CaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=128)
    by: str = Field(min_length=1, max_length=200)


class OutcomeReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding: Finding
    verification: Verification
    by: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(gateway: Gateway, token: str | None, eval_report: Path = EVAL_REPORT) -> FastAPI:
    app = FastAPI(title="Zeta One gateway")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(admin.AdminRefused)
    def refused(request: Request, error: admin.AdminRefused) -> JSONResponse:
        return _error(error.status, error.code, error.message)

    # Every error, the framework's included, has the demo API's shape.
    @app.exception_handler(HTTPException)
    def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return _error(error.status_code, f"http_{error.status_code}", str(error.detail))

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        return _error(422, "invalid_request", f"{len(error.errors())} invalid parameters")

    @app.exception_handler(Exception)
    def internal_error(request: Request, error: Exception) -> JSONResponse:
        return _error(500, "internal_error", type(error).__name__)

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

    @app.post("/v1/challenges/{challenge_id}/resolve")
    async def resolve(challenge_id: str, request: Request):
        admin.require_admin(request.headers, token)
        try:
            resolution = Resolution.model_validate_json(await request.body())
        except ValidationError as error:
            return _error(400, "invalid_resolution", str(error))
        try:
            return await run_in_threadpool(
                gateway.resolve, challenge_id, resolution.outcome, resolution.by, resolution.note,
                resolution.finding, resolution.verification,
            )
        except UnknownChallenge:
            return _error(404, "unknown_challenge", f"no challenge {challenge_id}")
        except NotHeld as error:
            return _error(409, "not_held", str(error))

    # --- Admin: agents and authorizations (S6). A person with the admin token, never an agent. ---

    def _admin_stores(request: Request):
        admin.require_admin(request.headers, token)
        stages = gateway.stages
        if stages.registry is None or stages.authorizations is None:
            raise admin.AdminRefused(503, "admin_unavailable", "this gateway has no registry or authorization store")
        return stages.registry, stages.authorizations

    def _body(model, raw: bytes):
        try:
            return model.model_validate_json(raw), None
        except ValidationError as error:
            return None, _error(400, "invalid_body", f"{error.error_count()} invalid fields")

    @app.post("/v1/agents", status_code=201)
    async def register_agent(request: Request):
        registry, _ = _admin_stores(request)
        registration, problem = _body(AgentRegistration, await request.body())
        if problem:
            return problem
        try:
            public_key = base64.b64decode(registration.public_key, validate=True)
        except (binascii.Error, ValueError):
            return _error(400, "invalid_public_key", "public_key must be base64")
        with gateway.lock:
            if registry.get(registration.agent_id) is not None:
                return _error(409, "agent_exists", f"agent {registration.agent_id} is already registered")
            try:
                agent = registry.register(registration.agent_id, registration.business_id, registration.owner,
                                          public_key, datetime.now(UTC))
            except ValueError:
                return _error(400, "invalid_public_key", "public_key must be a 32-byte Ed25519 key")
        return agent.model_dump(exclude={"public_key"})

    @app.post("/v1/agents/{agent_id}/revoke")
    def revoke_agent(agent_id: str, request: Request):
        registry, _ = _admin_stores(request)
        with gateway.lock:
            if registry.get(agent_id) is None:
                return _error(404, "unknown_agent", f"no agent {agent_id}")
            registry.revoke(agent_id, datetime.now(UTC))
            return registry.get(agent_id).model_dump(exclude={"public_key"})

    @app.post("/v1/authorizations", status_code=201)
    async def grant_authorization(request: Request):
        registry, authorizations = _admin_stores(request)
        authorization, problem = _body(Authorization, await request.body())
        if problem:
            return problem
        with gateway.lock:
            agent = registry.get(authorization.agent_id)
            if agent is None or agent.business_id != authorization.business_id:
                return _error(400, "unknown_agent", "the authorization must name a registered agent of its business")
            try:
                authorizations.grant(authorization)
            except ValueError as error:
                return _error(409, "invalid_grant", str(error))
        return authorization.model_dump(mode="json")

    @app.post("/v1/authorizations/{authorization_id}/revoke")
    def revoke_authorization(authorization_id: str, request: Request):
        _, authorizations = _admin_stores(request)
        with gateway.lock:
            if not authorizations.revoke(authorization_id, datetime.now(UTC)):
                return _error(404, "unknown_authorization", f"no current authorization {authorization_id}")
        return {"authorization_id": authorization_id, "status": "revoked"}

    @app.post("/v1/decisions/{decision_id}/outcomes", status_code=201)
    async def report_outcome(decision_id: str, request: Request):
        admin.require_admin(request.headers, token)
        report, problem = _body(OutcomeReport, await request.body())
        if problem:
            return problem
        try:
            outcome = gateway.report_outcome(decision_id, report.finding, report.verification, report.by, report.note)
        except UnknownDecision:
            return _error(404, "unknown_decision", f"no decision {decision_id}")
        return outcome.model_dump(mode="json")

    @app.get("/v1/adjustments")
    def list_adjustments(request: Request, business_id: str | None = None):
        admin.require_admin(request.headers, token)
        with gateway.lock:
            return [row.model_dump(mode="json") for row in gateway.adjustments.all(business_id)]

    @app.post("/v1/adjustments/{adjustment_id}/revoke", status_code=201)
    async def revoke_adjustment(adjustment_id: str, request: Request):
        admin.require_admin(request.headers, token)
        body, problem = _body(AdjustmentRevocation, await request.body())
        if problem:
            return problem
        with gateway.lock:
            revocation = gateway.adjustments.revoke(adjustment_id, body.by, gateway.clock(), body.reason)
        if revocation is None:
            return _error(404, "unknown_adjustment", f"no adjustment {adjustment_id}")
        return revocation.model_dump(mode="json")

    # --- Case review (decision 0015): an AI assembles evidence; a person decides. ---

    @app.post("/v1/cases", status_code=201)
    async def open_case(request: Request):
        admin.require_admin(request.headers, token)
        body, problem = _body(CaseRequest, await request.body())
        if problem:
            return problem
        try:
            return await run_in_threadpool(gateway.review, body.decision_id, body.by)
        except UnknownDecision:
            return _error(404, "unknown_decision", f"no decision {body.decision_id}")

    @app.get("/v1/cases/{case_id}")
    def get_case(case_id: str, request: Request):
        admin.require_admin(request.headers, token)
        with gateway.lock:
            case = gateway.cases.get(case_id)
        return case if case else _error(404, "unknown_case", f"no case {case_id}")

    @app.get("/v1/decisions/{decision_id}/cases")
    def decision_cases(decision_id: str, request: Request):
        admin.require_admin(request.headers, token)
        with gateway.lock:
            return gateway.cases.for_decision(decision_id)

    @app.get("/review", response_class=HTMLResponse)
    def review_page():
        """The case worker's page. It holds no data: it asks for the admin token and calls the API."""
        return REVIEW_PAGE.read_text()

    @app.get("/v1/stats")
    def stats(request: Request):
        admin.require_admin(request.headers, token)
        with gateway.lock:
            return gateway.ledger.stats()

    # Records name the signals and the model's rationale, which the agent's own response leaves out
    # (S4), so reading them is an admin action.
    @app.get("/v1/decisions")
    def list_decisions(request: Request, limit: int = 50) -> list[dict]:
        admin.require_admin(request.headers, token)
        with gateway.lock:
            return gateway.ledger.decisions(min(max(limit, 1), 500))

    @app.get("/v1/decisions/{decision_id}")
    def get_decision(decision_id: str, request: Request):
        admin.require_admin(request.headers, token)
        with gateway.lock:
            record = gateway.ledger.decision(decision_id)
        if record is None:
            return _error(404, "unknown_decision", f"no decision {decision_id}")
        return record

    @app.get("/v1/scenarios")
    def list_scenarios() -> list[dict]:
        return scenarios.list_scenarios()

    @app.post("/v1/scenarios/{name}/run")
    def run_scenario(name: str, request: Request):
        # A JSON content type can't be sent cross-site without a CORS preflight, which only local
        # origins pass, so another web page can't write sandbox records into this gateway.
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return _error(415, "json_required", "send Content-Type: application/json")
        try:
            result = scenarios.run(name)
        except KeyError:
            return _error(404, "unknown_scenario", f"no scenario named {name}")
        with gateway.lock:
            gateway.ledger.save_record(result.decision_record)
        return scenarios.dump(result)

    @app.get("/v1/eval/latest")
    def eval_latest():
        if not eval_report.exists():
            return _error(404, "no_report", "no evaluation report yet")
        return json.loads(eval_report.read_text())

    return app


def default_gateway() -> Gateway:
    connection = db.connect()
    stages = real_stages(connection, configuration=configuration_from_env())
    register_demo_agents(stages)
    return Gateway(stages=stages, ledger=Ledger(connection), reuse=RiskReuse(connection), version=engine_version())


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """`app` for uvicorn (`zeta_one.gateway.app:app`), built on first access."""
    global _app
    if name != "app":
        raise AttributeError(name)
    if _app is None:
        _app = create_app(default_gateway(), admin.admin_token())
    return _app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(__getattr__("app"), host=HOST, port=8000)
