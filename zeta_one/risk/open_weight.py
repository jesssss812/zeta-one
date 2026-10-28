"""The open-weight comparison tier: an open-weight model in the strong tier's place (decision 0009).

It gets the strong tier's system prompt and rendered request (gateway facts, then untrusted text in
bounded blocks) and must answer the same schema, through any OpenAI-compatible chat API: OpenRouter
by default, or another provider by setting OPEN_WEIGHT_BASE_URL. The answer is handled exactly as
the strong tier's: evidence kept only where the request named it, the level at least the worst
signal, and its self-reported confidence never used.

`OpenWeightTier.assess` never raises: a missing key, an HTTP error, a refusal, a truncated or
invalid answer comes back as `result.error`, which the policy challenges. The model id, prices and
the provider's support for JSON output are unverified until the first live call.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from zeta_one.contracts import RiskInput, TierOutput, TierResult, Usage
from zeta_one.risk import claude

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-235b-a22b-2507"
TIMEOUT_SECONDS = 60.0
MAX_TOKENS = 4096
ROOT = Path(__file__).resolve().parents[2]
# Without reported usage the input is estimated high, so spend is never undercounted.
CHARS_PER_TOKEN_ESTIMATE = 2

SYSTEM_PROMPT = (
    claude.SYSTEM_PROMPT
    + "\n\n## Output format\n\nReply with one JSON object and nothing else, matching this JSON schema:\n\n"
    + json.dumps(claude.StrongAnswer.model_json_schema(), indent=1)
)


def setting(name: str, env_file: Path | None = None) -> str | None:
    """A setting from the environment, else from `.env`; never printed or logged."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = env_file or ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip().removeprefix("export ").strip() == name and value.strip():
                return value.strip().strip("'\"")
    return None


def prices() -> dict[str, tuple[float, float]]:
    """USD per million (input, output) tokens from OPEN_WEIGHT_PRICES ("0.2,0.6"); empty if unset, so
    the cost lists the model as unpriced rather than free."""
    raw = setting("OPEN_WEIGHT_PRICES")
    if not raw:
        return {}
    input_price, output_price = (float(part) for part in raw.split(","))
    return {model(): (input_price, output_price)}


def model() -> str:
    return setting("OPEN_WEIGHT_MODEL") or DEFAULT_MODEL


class OpenWeightTier:
    """A `RiskTier` named `open_weight`. Pass `post` to stub the HTTP call in tests:
    post(url, headers, body) -> (status_code, json)."""

    name = "open_weight"

    def __init__(self, post: Any = None, key: str | None = None, model_id: str | None = None,
                 base_url: str | None = None) -> None:
        self._post = post
        self._key = key
        self.model = model_id or model()
        self._base_url = (base_url or setting("OPEN_WEIGHT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    def assess(self, risk_input: RiskInput) -> TierOutput:
        started = time.monotonic()
        key = self._key or setting("OPEN_WEIGHT_API_KEY") or setting("OPENROUTER_API_KEY")
        if not key and self._post is None:
            return self._failed(started, None, "OPEN_WEIGHT_API_KEY is not set")
        user = claude.render(risk_input)
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
        }
        try:
            status, payload = (self._post or _http_post)(f"{self._base_url}/chat/completions",
                                                         {"Authorization": f"Bearer {key}"}, body)
        except Exception as error:  # timeouts and connection errors
            return self._failed(started, None, type(error).__name__)
        if status != 200:
            return self._failed(started, None, f"http_{status}")
        usage = _usage(payload, SYSTEM_PROMPT + user)
        try:
            choice = payload["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            return self._failed(started, usage, "invalid_output: no choice")
        if message.get("refusal"):
            return self._failed(started, usage, "refusal")
        if choice.get("finish_reason") != "stop":
            return self._failed(started, usage, f"invalid_output: finish_reason {choice.get('finish_reason')}")
        try:
            answer = claude.StrongAnswer.model_validate_json(_json_text(message.get("content") or ""))
        except ValidationError as error:
            return self._failed(started, usage, f"invalid_output: {error.error_count()} schema errors")
        return claude.answer_output(answer, risk_input, "open_weight", self.model, _since(started), usage)

    def _failed(self, started: float, usage: Usage | None, error: str) -> TierOutput:
        return TierOutput(result=TierResult(tier="open_weight", model=self.model, latency_ms=_since(started),
                                            usage=usage, error=error))


def _http_post(url: str, headers: dict[str, str], body: dict) -> tuple[int, Any]:
    response = httpx.post(url, headers=headers, json=body, timeout=TIMEOUT_SECONDS)
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


def _json_text(content: str) -> str:
    """The JSON object in a reply, without a Markdown code fence some models add."""
    fenced = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", content, re.DOTALL)
    return fenced.group(1) if fenced else content


def _usage(payload: Any, sent: str) -> Usage:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    prompt = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    completion = usage.get("completion_tokens") if isinstance(usage, dict) else None
    if isinstance(prompt, int) and isinstance(completion, int):
        return Usage(input_tokens=prompt, output_tokens=completion)
    return Usage(input_tokens=len(sent) // CHARS_PER_TOKEN_ESTIMATE + 1, output_tokens=MAX_TOKENS, estimated=True)


def _since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
