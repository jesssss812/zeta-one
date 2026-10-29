"""The open-weight comparison tier: an open-weight model in the strong tier's place (decisions 0014,
0018 and 0019).

It gets the strong tier's system prompt, plus a section on what the business's confirmation records
mean, and its rendered request (gateway facts, then untrusted text in bounded blocks), and must
answer the same schema, through any OpenAI-compatible chat API: OpenRouter with DEFAULT_MODEL by
default, or another server by setting OPEN_WEIGHT_BASE_URL and OPEN_WEIGHT_MODEL. The evaluation
points it at a vLLM server running Qwen 3.6 27B on a rented GPU (decision 0018). The answer is
handled exactly as the strong tier's: evidence kept only where the request named it, the level at
least the worst signal, and its self-reported confidence never used.

`OpenWeightTier.assess` never raises: a missing key, an HTTP error, a refusal, a truncated or
invalid answer comes back as `result.error`, which the policy challenges. A model with neither
OPEN_WEIGHT_GPU_HOURLY nor OPEN_WEIGHT_PRICES is listed as unpriced, never as free.
"""

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from zeta_one.contracts import GpuRate, Price, RiskInput, TierOutput, TierResult, Usage
from zeta_one.risk import claude
from zeta_one.settings import setting

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-235b-a22b-2507"
TIMEOUT_SECONDS = 60.0
MAX_TOKENS = 4096
# Without reported usage the input is estimated high, so spend is never undercounted.
CHARS_PER_TOKEN_ESTIMATE = 2

ANSWER_SCHEMA = claude.StrongAnswer.model_json_schema()
# The strong tier's prompt, plus what the business's confirmation records mean (decision 0019).
RECORDS_NOTE = (Path(__file__).parent / "prompts" / "open_weight_records.md").read_text()
SYSTEM_PROMPT = (
    claude.SYSTEM_PROMPT
    + "\n" + RECORDS_NOTE
    + "\n## Output format\n\nReply with one JSON object and nothing else, matching this JSON schema:\n\n"
    + json.dumps(ANSWER_SCHEMA, indent=1)
)


def prices() -> dict[str, Price]:
    """The model's price: a self-hosted GPU's hourly rent from OPEN_WEIGHT_GPU_HOURLY ("0.59"), else
    USD per million (input, output) tokens from OPEN_WEIGHT_PRICES ("0.2,0.6"); empty if neither is
    set, so the cost lists the model as unpriced rather than free."""
    hourly = setting("OPEN_WEIGHT_GPU_HOURLY")
    if hourly:
        return {model(): GpuRate(float(hourly))}
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
            # The answer's schema is enforced while decoding, where the server supports it, and the
            # model answers directly: Qwen-style chat templates otherwise think first.
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "risk_answer", "schema": ANSWER_SCHEMA}},
            "chat_template_kwargs": {"enable_thinking": False},
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
