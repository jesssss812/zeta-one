import json
from pathlib import Path

import pytest

from zeta_one.contracts import ScenarioResult

FIXTURES = sorted((Path(__file__).resolve().parents[1] / "data" / "fixtures").glob("*.json"))


@pytest.fixture(params=FIXTURES, ids=lambda path: path.stem)
def fixture_raw(request) -> dict:
    return json.loads(request.param.read_text())


@pytest.fixture
def scenario(fixture_raw) -> ScenarioResult:
    return ScenarioResult.model_validate(fixture_raw)


MODEL_SETTINGS = ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "TYPESAFE_API_KEY", "OPEN_WEIGHT_API_KEY",
                  "OPEN_WEIGHT_BASE_URL", "OPEN_WEIGHT_MODEL", "OPEN_WEIGHT_PRICES", "OPEN_WEIGHT_GPU_HOURLY",
                  "CHAT_API_KEY", "CHAT_BASE_URL", "CHAT_MODEL")


@pytest.fixture(autouse=True)
def no_real_model_settings(request, tmp_path_factory, monkeypatch):
    """Keep every test away from the real `.env` and the shell's model keys, addresses and prices, so no
    test makes a paid call by accident or depends on the owner's set-up. Tests marked live_models keep
    them."""
    if "live_models" in request.keywords:
        return
    from zeta_one import settings

    monkeypatch.setattr(settings, "ROOT", tmp_path_factory.mktemp("no_env"))
    for name in MODEL_SETTINGS:
        monkeypatch.delenv(name, raising=False)
