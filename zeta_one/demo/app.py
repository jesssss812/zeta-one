"""The one-screen demo: the feedback-loop story, one step per click, on a sandbox gateway.

    .venv/bin/uvicorn zeta_one.demo.app:app --port 8001          # open http://127.0.0.1:8001/demo
    ZETA_DEMO_LIVE=1 .venv/bin/uvicorn zeta_one.demo.app:app --port 8001   # escalations call Claude (paid)

`/demo` steps through the story and resets it. Every other path is the sandbox gateway itself, so
`/review` shows the sandbox's decisions with their evidence and source records. The sandbox holds
only synthetic data in memory, and its admin token is made for this process and handed to the demo
page, so the review page opens without setup; it is never the gateway's real admin token. Paid model
calls happen only when the server was started with ZETA_DEMO_LIVE=1, never because of a click.
"""

import os
import secrets
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from zeta_one.demo.story import TITLES, Story
from zeta_one.review.explain import summary

PAGE = Path(__file__).resolve().parent / "page.html"


class ModelsOff(Exception):
    """The case assistant's model was asked for while the demo runs without models."""


class _NoModel:
    """The case assistant's client when models are off: every call fails, so the case shows only the
    gathered evidence and says why."""

    class messages:
        @staticmethod
        def create(**_: Any) -> Any:
            raise ModelsOff("models are off in this demo")


class DemoServer:
    """An ASGI app: the demo's own routes, and the current sandbox gateway for everything else."""

    def __init__(self, live_models: bool = False, review_client: Any = None) -> None:
        self.live_models = live_models
        self._review_client = review_client if review_client is not None or live_models else _NoModel()
        self.token = secrets.token_urlsafe(24)
        self._lock = threading.Lock()
        self.story = self._new_story()
        self.control = self._control_app()

    def _new_story(self) -> Story:
        return Story(self.token, live_models=self.live_models, review_client=self._review_client)

    def state(self) -> dict[str, Any]:
        steps = []
        for step in self.story.steps:
            decision = step.get("decision")
            if decision:
                record = self.story.gateway.ledger.decision(decision["decision_id"])
                step = step | {"summary": summary(record)} if record else step
            steps.append(step)
        return {"titles": list(TITLES), "steps": steps, "done": self.story.done, "live_models": self.live_models,
                "review_token": self.token, "simulated": True}

    def _control_app(self) -> FastAPI:
        control = FastAPI(title="Zeta One demo")

        def json_only(request: Request) -> JSONResponse | None:
            # As for scenario runs: a JSON body can't be sent cross-site without a preflight.
            if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                return JSONResponse(status_code=415, content={"error": {"code": "json_required",
                                                                        "message": "send Content-Type: application/json"}})
            return None

        @control.get("/demo", response_class=HTMLResponse)
        def page():
            return PAGE.read_text()

        @control.get("/")
        def root():
            return RedirectResponse("/demo")

        @control.get("/v1/demo")
        def current():
            with self._lock:
                return self.state()

        @control.post("/v1/demo/next")
        def advance(request: Request):
            if problem := json_only(request):
                return problem
            with self._lock:
                self.story.next()
                return self.state()

        @control.post("/v1/demo/reset")
        def reset(request: Request):
            if problem := json_only(request):
                return problem
            with self._lock:
                self.story.close()
                self.story = self._new_story()
                return self.state()

        return control

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or path in ("/", "/demo", "/v1/demo") or path.startswith("/v1/demo/"):
            await self.control(scope, receive, send)
        else:
            await self.story.app(scope, receive, send)


_app: DemoServer | None = None


def __getattr__(name: str) -> DemoServer:
    """`app` for uvicorn (`zeta_one.demo.app:app`), built on first access."""
    global _app
    if name != "app":
        raise AttributeError(name)
    if _app is None:
        _app = DemoServer(live_models=os.environ.get("ZETA_DEMO_LIVE") == "1")
    return _app
