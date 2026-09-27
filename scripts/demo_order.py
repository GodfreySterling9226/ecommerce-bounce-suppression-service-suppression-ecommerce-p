"""Send one checkout notice through the same workflow used by the service."""

import os

from src.infrai_email import InfraiEmailClient
from src.order_updates import OrderNotice, OrderStage, OrderUpdateService


def main() -> None:
    recipient = os.environ.get("DEMO_EMAIL_TO", "")
    if not recipient:
        raise SystemExit("DEMO_EMAIL_TO is required")
    client = InfraiEmailClient(os.environ.get("INFRAI_API_KEY", ""))
    decision = OrderUpdateService(client).deliver(
        OrderNotice(
            event_id="demo-checkout-001",
            order_id="ORDER-1042",
            customer_email=recipient,
            stage=OrderStage.CHECKOUT,
            detail="Payment accepted; fulfillment is next.",
        )
    )
    print(decision)


if __name__ == "__main__":
    main()
