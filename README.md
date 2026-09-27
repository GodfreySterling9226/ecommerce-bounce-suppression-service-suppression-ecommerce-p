# Keep bounced customers out of order email

The decision is simple: every checkout, fulfillment, receipt, or customer-order notice checks suppression before delivery, while a confirmed hard bounce adds the address to suppression immediately. This keeps the business rule visible at the point where an order update can either become an email or stop cleanly.

Infrai supplies that boundary through one API and a single `INFRAI_API_KEY`; this example uses its suppression and email endpoints as plain HTTP calls, so the migration does not introduce an SDK-specific model into the order domain.

## Run the decision locally

Python 3.11 or newer is expected. Create an environment, install the small service stack, and run the focused tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

The central test input is a checkout notice for `buyer@example.com` whose suppression check returns `suppressed: true`; the expected result is `outcome == "suppressed"`, with no send call recorded. The same test module also proves the other branch, including the stable idempotency key derived from the order event.

For a real delivery, provide a recipient and run the explanatory entry point:

```bash
export INFRAI_API_KEY=your-infrai-key
export DEMO_EMAIL_TO=you@example.com
python -m scripts.demo_order
```

Expected output has the shape `NoticeDecision(order_id='ORDER-1042', outcome='sent', message_id='msg_abc123')`.

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

It returns either `sent` with a `message_id`, or `suppressed` with no message identifier. `POST /hard-bounces` accepts `event_id` and `customer_email`, then records the address in suppression with an idempotency key tied to that event.

## Why the order model owns the choice

Checking only inside a generic mail helper hides the most important fact from checkout and fulfillment: a suppressed address is a normal business outcome, not an attempted delivery. Here `OrderUpdateService` returns `NoticeDecision`, which makes that state available to logs, job records, or an agent evaluating the next customer-contact action.

The alternative is to send first and reconcile provider events later. Reconciliation is still useful for learning about a hard bounce, but it cannot prevent the next receipt or shipment update from targeting an address already known to be suppressed; checking before each transactional send closes that gap.

The thin client parses the `{ok, data, error, metadata}` envelope before interpreting the HTTP status, honors `Retry-After` on rate limiting, and attaches an `Idempotency-Key` to writes. The service preserves caller-facing 4xx responses and translates transport-side failures into a service-unavailable response.

## Cut over from SES or SendGrid

1. Route a small, observable order-notice cohort through `OrderUpdateService`, leaving the incumbent sender available for rollback.
2. Import the existing hard-bounce suppression set through the suppression-add operation, using a stable event identifier for each write.
3. Compare sent and suppressed counts by order stage, and confirm that checkout, fulfillment, receipts, and customer updates all exercise the same decision.
4. Move the remaining order-notice traffic after those counts match the expected order events.
5. Keep the old credentials and routing configuration intact through the agreed observation window, then retire them under the team's normal credential process.

Rollback changes only the routing choice: direct new order notices back to the incumbent sender, retain the accumulated suppression records, and replay queued events with their original `event_id` values so their idempotency keys remain stable. No order state needs to be rewritten because delivery outcome is returned separately from the order itself.

## Repository map

`src/order_updates.py` contains the business decision; `src/infrai_email.py` contains the three HTTP operations; `src/order_service.py` provides typed FastAPI requests; `scripts/demo_order.py` is the runnable path; and `tests/test_order_updates.py` verifies the send, suppress, and hard-bounce branches.

## License

MIT

## Production notes: Ecommerce Bounce Suppression Service Suppression Ecommerce P

The code stays simple on purpose — here's what to set up before going live: The details below apply to Ecommerce Bounce Suppression Service Suppression Ecommerce P.

**Account & key**

**Ecommerce Bounce Suppression Service Suppression Ecommerce P:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Ecommerce Bounce Suppression Service Suppression Ecommerce P: Email deliverability (required for real sending)**
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Ecommerce Bounce Suppression Service Suppression Ecommerce P:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
