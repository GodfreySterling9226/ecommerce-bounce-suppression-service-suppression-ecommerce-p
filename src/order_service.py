"""FastAPI boundary for order notices and hard-bounce ingestion."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .infrai_email import InfraiEmailClient, InfraiError, InfraiTransportError
from .order_updates import OrderNotice, OrderStage, OrderUpdateService


class OrderNoticeRequest(BaseModel):
    event_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    customer_email: EmailStr
    stage: OrderStage
    detail: str = Field(min_length=1)


class OrderNoticeResponse(BaseModel):
    order_id: str
    outcome: Literal["sent", "suppressed"]
    message_id: str | None


class HardBounceRequest(BaseModel):
    event_id: str = Field(min_length=1)
    customer_email: EmailStr


class HardBounceResponse(BaseModel):
    customer_email: EmailStr
    outcome: Literal["suppressed"]


app = FastAPI(title="E-commerce email suppression service")


def _workflow() -> OrderUpdateService:
    key = os.environ.get("INFRAI_API_KEY", "")
    return OrderUpdateService(InfraiEmailClient(key))


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, InfraiError):
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    if isinstance(exc, (InfraiTransportError, ValueError)):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise exc


@app.post("/order-notices", response_model=OrderNoticeResponse)
def send_order_notice(request: OrderNoticeRequest) -> OrderNoticeResponse:
    try:
        decision = _workflow().deliver(
            OrderNotice(
                event_id=request.event_id,
                order_id=request.order_id,
                customer_email=str(request.customer_email),
                stage=request.stage,
                detail=request.detail,
            )
        )
    except (InfraiError, InfraiTransportError, ValueError) as exc:
        _raise_http(exc)
    return OrderNoticeResponse(**decision.__dict__)


@app.post("/hard-bounces", response_model=HardBounceResponse)
def record_hard_bounce(request: HardBounceRequest) -> HardBounceResponse:
    try:
        outcome = _workflow().record_hard_bounce(
            event_id=request.event_id,
            customer_email=str(request.customer_email),
        )
    except (InfraiError, InfraiTransportError, ValueError) as exc:
        _raise_http(exc)
    return HardBounceResponse(customer_email=request.customer_email, outcome=outcome)
