"""Rho's data shapes, as far as the engine reads them.

Written by hand from Rho's public OpenAPI description (https://docs.rho.co/api/v1/openapi).
Fields the engine doesn't read are left out.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class Money(BaseModel):
    """Integer minor units and an ISO 4217 code: Money(amount=125000, currency="USD") is $1,250.00.

    The amount is a strict integer: JSON `true`, `"100"` or `100.0` are refused, not coerced."""

    model_config = ConfigDict(frozen=True)

    amount: StrictInt
    currency: str


class Business(BaseModel):
    id: str
    legal_name: str


class Account(BaseModel):
    id: str
    account_type: str
    balance: Money
    account_name: str | None = None


class CounterpartyPaymentMethod(BaseModel):
    id: str | None
    type: str
    is_default: bool
    bank_name: str | None = None


class Counterparty(BaseModel):
    id: str
    legal_name: str
    status: str
    is_business: bool = True
    payment_methods: list[CounterpartyPaymentMethod] = Field(default_factory=list)
    email: str | None = None
    created_at: datetime
    updated_at: datetime


class BillCounterparty(BaseModel):
    id: str


class BillTransaction(BaseModel):
    id: str


class Bill(BaseModel):
    id: str
    status: str
    amount: Money | None = None
    counterparty: BillCounterparty | None = None
    transaction: BillTransaction | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    memo: str | None = None
    lines: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Transaction(BaseModel):
    id: str
    account_id: str
    transaction_type: str
    status: str
    amount: Money
    counterparty_name: str
    posted_at: datetime | None = None
    initiated_at: datetime
