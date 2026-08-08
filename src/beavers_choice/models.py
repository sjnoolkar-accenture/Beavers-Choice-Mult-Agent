"""Typed domain models shared by services and agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class LineItem:
    requested_name: str
    item_name: str | None
    quantity: int


class QuoteLine(BaseModel):
    item_name: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    line_total: Decimal = Field(gt=0)
    discount_rate: Decimal = Field(ge=0, le=1)


class ReorderDecision(BaseModel):
    approved: bool
    arrival: str
    reason: str | None = None
    cost: Decimal = Decimal("0")
    transaction_id: int | None = None


class ProcessResult(BaseModel):
    status: Literal["fulfilled", "rejected"]
    fulfilled: bool
    request_date: str
    promised_date: str | None
    total_amount: Decimal
    response: str
    items: list[dict[str, Any]]


class EvaluationSummary(BaseModel):
    requests: int
    fulfilled: int
    rejected: int
    cash_changes: int
    results_path: str
