import sqlite3

import pytest

from zeta_one.contracts import ScenarioResult
from zeta_one.gateway.ledger import Ledger
from zeta_one.gateway.scenarios import load_fixture


@pytest.fixture
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


@pytest.fixture
def ledger(connection) -> Ledger:
    return Ledger(connection)


@pytest.fixture
def held_scenario() -> ScenarioResult:
    return load_fixture("vendor_payment_method_changed")


@pytest.fixture
def routine_scenario() -> ScenarioResult:
    return load_fixture("routine_bill_payment")
