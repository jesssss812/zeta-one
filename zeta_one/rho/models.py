"""Rho's data shapes, as far as the engine reads them.

Written by hand from docs/reference/rho-openapi.json. Fields the engine doesn't read are left out.
"""

from pydantic import BaseModel, ConfigDict


class Money(BaseModel):
    """Integer minor units and an ISO 4217 code: Money(amount=125000, currency="USD") is $1,250.00."""

    model_config = ConfigDict(frozen=True)

    amount: int
    currency: str
