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
