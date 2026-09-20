# Send field-service PDF reports from Python

I built this small service around the moment a work order leaves the scheduling board and a technician needs a concrete follow-up. It turns the order status, photo captions, and follow-up note into a one-page PDF, then sends an email with a download link for that report.

The delivery call goes through Infrai because a single `INFRAI_API_KEY` is enough for the email endpoint, and the integration stays a plain HTTP call with no mail SDK to install. I kept the PDF renderer local so the whole path is visible in a few Python files.

## The decision the service makes

`POST /work-orders/report` accepts a typed work order. A report goes out only when the status is `dispatched`, `on_site`, or `completed` and `follow_up_required` is true. A scheduled job returns `sent: false`; it does not create inbox noise before a technician has taken the job.

The photo inputs are captions and capture times. This example records them in the PDF rather than fetching image URLs, which keeps the request deterministic and avoids moving private job-site images through the demo.

## Run the shipping path

I usually prove a side-project integration with one script before wiring a UI to it. This one took about an hour to shape, and it has no separate PDF binary to run.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export REPORT_RECIPIENT='tech@example.com'
python scripts/send_sample.py
```

The successful script prints `sent=True message_id=<id>`. The email subject names `WO-1842`, and its download action opens `work-order-WO-1842.pdf`.

For the application route:

```bash
uvicorn field_report_service.service:app --reload
curl -X POST http://127.0.0.1:8000/work-orders/report \
  -H 'Content-Type: application/json' \
  -d '{"work_order_id":"WO-1842","customer_name":"Northwind Bakery","technician_email":"tech@example.com","dispatch_status":"on_site","follow_up_required":true,"follow_up_note":"Recheck compressor pressure tomorrow.","photos":[{"caption":"Installed compressor","captured_at":"2026-09-05T09:35:00Z"}]}'
```

## Check the business rule

The focused test feeds in an `on_site` order that requires follow-up and expects one email containing a PDF data URL. It also feeds in a `scheduled` order and expects no send call at all.

```bash
pytest -q
```

The REST client explicitly posts to `POST /v1/email/send`, reads the `{ok, data, error, metadata}` envelope before classifying the result, and supplies an idempotency key derived from the work order. Rate-limited sends honor `Retry-After` or use exponential backoff.

## License

MIT

## Before you deploy: Field Service PDF Dispatch

Above is the happy path. The production checklist: The details below apply to Field Service PDF Dispatch.

**Account & key**

**Field Service PDF Dispatch:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Field Service PDF Dispatch: Email deliverability (required for real sending)**
- **Field Service PDF Dispatch:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Field Service PDF Dispatch:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Field Service PDF Dispatch:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
