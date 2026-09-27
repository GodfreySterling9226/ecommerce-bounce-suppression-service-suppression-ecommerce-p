"""Business decisions for transactional order email and hard bounces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class OrderStage(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    CUSTOMER_UPDATE = "customer_update"


class EmailGateway(Protocol):
    def suppression_check(self, email: str) -> dict[str, Any]:
        raise AssertionError("Protocol method")

    def suppression_add(self, email: str, *, idempotency_key: str) -> dict[str, Any]:
        raise AssertionError("Protocol method")

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        text: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        raise AssertionError("Protocol method")


@dataclass(frozen=True)
class OrderNotice:
    event_id: str
    order_id: str
    customer_email: str
    stage: OrderStage
    detail: str


@dataclass(frozen=True)
class NoticeDecision:
    order_id: str
    outcome: str
    message_id: str | None


class OrderUpdateService:
    def __init__(self, email: EmailGateway) -> None:
        self._email = email

    def deliver(self, notice: OrderNotice) -> NoticeDecision:
        suppression = self._email.suppression_check(notice.customer_email)
        if bool(suppression.get("suppressed")):
            return NoticeDecision(notice.order_id, "suppressed", None)

        result = self._email.send_email(
            to=notice.customer_email,
            subject=self._subject(notice),
            text=self._body(notice),
            idempotency_key=f"order-notice:{notice.event_id}",
        )
        return NoticeDecision(notice.order_id, "sent", str(result["message_id"]))

    def record_hard_bounce(self, *, event_id: str, customer_email: str) -> str:
        self._email.suppression_add(
            customer_email,
            idempotency_key=f"hard-bounce:{event_id}",
        )
        return "suppressed"

    @staticmethod
    def _subject(notice: OrderNotice) -> str:
        labels = {
            OrderStage.CHECKOUT: "Order confirmed",
            OrderStage.FULFILLMENT: "Order shipped",
            OrderStage.RECEIPT: "Your receipt",
            OrderStage.CUSTOMER_UPDATE: "Order update",
        }
        return f"{labels[notice.stage]}: {notice.order_id}"

    @staticmethod
    def _body(notice: OrderNotice) -> str:
        return f"Order {notice.order_id}: {notice.detail}"
