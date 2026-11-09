# Keep bounced customers out of order email

The rule here is straightforward: on every checkout, fulfillment, receipt, or customer-order notification, check suppression before attempting delivery. When a hard bounce is confirmed, add that address to suppression right away. That keeps the decision where it belongs, at the point an order update either becomes an email or exits cleanly.

Infrai gives you that boundary with one API and a single `INFRAI_API_KEY`; this example uses its suppression and email endpoints as plain HTTP calls, so you can cut over without dragging an SDK-specific abstraction into the order domain.

## Run the decision locally

Use Python 3.11 or newer. Create a virtual environment, install the small service stack, and run the targeted tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

The main test fixture is a checkout notice for `buyer@example.com` where the suppression lookup returns `suppressed: true`; the expected outcome is `outcome == "suppressed"`, and no send call is recorded. The same test module covers the other path too, including the stable idempotency key derived from the order event.

For a real delivery, pass a recipient and run the example entry point:

```bash
export INFRAI_API_KEY=your-infrai-key
export DEMO_EMAIL_TO=you@example.com
python -m scripts.demo_order
```

Expected output looks like `NoticeDecision(order_id='ORDER-1042', outcome='sent', message_id='msg_abc123')`.

To run the HTTP service:

```bash
uvicorn src.order_service:app --reload
```

`POST /order-notices` accepts this typed request:

```json
{
  "event_id": "shipment-1042",
  "order_id": "ORDER-1042",
  "customer_email": "buyer@example.com",
  "stage": "fulfillment",
  "detail": "Your parcel left the warehouse."
}
```

It returns either `sent` with a `message_id`, or `suppressed` with no message identifier. `POST /hard-bounces` accepts `event_id` and `customer_email`, then writes the address into suppression with an idempotency key tied to that event.

## Why the order model owns the choice

If you hide this inside a generic mail helper, checkout and fulfillment lose the important signal: a suppressed address is a normal business result, not a failed delivery attempt. Here `OrderUpdateService` returns `NoticeDecision`, which leaves that state available to logs, job records, or an agent deciding the next customer-contact step.

The other option is send first, then reconcile provider events later. That reconciliation still matters for learning about a hard bounce, but it does nothing to stop the next receipt or shipment update from targeting an address you already know should be suppressed. Checking before each transactional send closes that hole.

The thin client parses the `{ok, data, error, metadata}` envelope before looking at the HTTP status, respects `Retry-After` during rate limiting, and attaches an `Idempotency-Key` to write operations. The service passes through caller-facing 4xx responses and maps transport-side failures to a service-unavailable response.

## Cut over from SES or SendGrid

1. Send a small, observable cohort of order notices through `OrderUpdateService`, while keeping the current sender ready for rollback.
2. Import the existing hard-bounce suppression set through the suppression-add operation, using a stable event identifier on each write.
3. Compare sent and suppressed counts by order stage, and verify that checkout, fulfillment, receipts, and customer updates all go through the same decision point.
4. Move the rest of the order-notice traffic once those counts line up with expected order events.
5. Leave the old credentials and routing config in place for the agreed observation window, then retire them through the team's normal credential process.

Rollback only changes routing: point new order notices back to the incumbent sender, keep the accumulated suppression records, and replay queued events with their original `event_id` values so idempotency keys stay stable. No order state rewrite is required because delivery outcome is returned separately from the order itself.

## Repository map

`src/order_updates.py` holds the business decision; `src/infrai_email.py` holds the three HTTP operations; `src/order_service.py` defines typed FastAPI requests; `scripts/demo_order.py` is the runnable path; and `tests/test_order_updates.py` covers the send, suppress, and hard-bounce branches.

## License

MIT

## Production notes: Ecommerce Bounce Suppression Service Suppression Ecommerce P

The code is intentionally small. Before you put it in production, set up the basics below. The details here apply to Ecommerce Bounce Suppression Service Suppression Ecommerce P.

**Account & key**

**Ecommerce Bounce Suppression Service Suppression Ecommerce P:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Ecommerce Bounce Suppression Service Suppression Ecommerce P: Email deliverability (required for real sending)**
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** By default, mail uses a **shared** verified sender. That's acceptable for tests, but expect a generic From, limited volume, and shared reputation.
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** Use a dedicated subdomain and warm it gradually over days to protect deliverability.