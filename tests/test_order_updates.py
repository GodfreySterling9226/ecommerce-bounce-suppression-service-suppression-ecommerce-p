from typing import Any

from src.order_updates import OrderNotice, OrderStage, OrderUpdateService


class RecordingEmailGateway:
    def __init__(self, *, suppressed: bool) -> None:
        self.suppressed = suppressed
        self.sent: list[dict[str, Any]] = []
        self.added: list[tuple[str, str]] = []

    def suppression_check(self, email: str) -> dict[str, Any]:
        return {"email": email, "suppressed": self.suppressed}

    def suppression_add(self, email: str, *, idempotency_key: str) -> dict[str, Any]:
        self.added.append((email, idempotency_key))
        return {"email": email}

    def send_email(self, **request: Any) -> dict[str, Any]:
        self.sent.append(request)
        return {"message_id": "msg_1042"}


def checkout_notice() -> OrderNotice:
    return OrderNotice(
        event_id="checkout-1042",
        order_id="ORDER-1042",
        customer_email="buyer@example.com",
        stage=OrderStage.CHECKOUT,
        detail="Payment accepted.",
    )


def test_suppressed_customer_is_not_emailed() -> None:
    gateway = RecordingEmailGateway(suppressed=True)

    decision = OrderUpdateService(gateway).deliver(checkout_notice())

    assert decision.outcome == "suppressed"
    assert decision.message_id is None
    assert gateway.sent == []


def test_eligible_customer_receives_idempotent_order_notice() -> None:
    gateway = RecordingEmailGateway(suppressed=False)

    decision = OrderUpdateService(gateway).deliver(checkout_notice())

    assert decision.outcome == "sent"
    assert decision.message_id == "msg_1042"
    assert gateway.sent[0]["idempotency_key"] == "order-notice:checkout-1042"


def test_hard_bounce_adds_customer_to_suppression() -> None:
    gateway = RecordingEmailGateway(suppressed=False)

    outcome = OrderUpdateService(gateway).record_hard_bounce(
        event_id="bounce-77", customer_email="buyer@example.com"
    )

    assert outcome == "suppressed"
    assert gateway.added == [("buyer@example.com", "hard-bounce:bounce-77")]
