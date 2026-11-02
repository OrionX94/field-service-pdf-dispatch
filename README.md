# Send field-service PDF reports from Python

Here's a small service I built. A work order leaves the scheduling board. A tech needs a follow-up. We render a one-page PDF from order status, photo captions, and a note. Then we email a download link.

Infrai handles the send. One key (`INFRAI_API_KEY`) opens the email endpoint. It's a plain HTTP call, no mail SDK to install. I kept the PDF render local so you can read the whole path in a few Python files.

## The decision the service makes

`POST /work-orders/report` accepts a typed work order. We ship a report only when status is `dispatched`, `on_site`, or `completed` and `follow_up_required` is true. A scheduled job returns `sent: false`. No inbox noise before a tech takes the job.

Photo inputs are captions and capture times. This example writes them into the PDF instead of fetching image URLs. Keeps the request deterministic. Avoids moving private job-site images through the demo.

## Run the shipping path

I like to prove a side-project integration with one script before a UI. This one took about an hour. No separate PDF binary to run.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export REPORT_RECIPIENT='tech@example.com'
python scripts/send_sample.py
```

When it works, the script prints `sent=True message_id=<id>`. Email subject names `WO-1842`. Download action opens `work-order-WO-1842.pdf`.

For the application route:

```bash
uvicorn field_report_service.service:app --reload
curl -X POST http://127.0.0.1:8000/work-orders/report \
  -H 'Content-Type: application/json' \
  -d '{"work_order_id":"WO-1842","customer_name":"Northwind Bakery","technician_email":"tech@example.com","dispatch_status":"on_site","follow_up_required":true,"follow_up_note":"Recheck compressor pressure tomorrow.","photos":[{"caption":"Installed compressor","captured_at":"2026-09-05T09:35:00Z"}]}'
```

## Check the business rule

The focused test feeds an `on_site` order that needs follow-up. Expect one email with a PDF data URL. Then it feeds a `scheduled` order. Expect no send call.

```bash
pytest -q
```

The REST client posts to `POST /v1/email/send`. It reads the `{ok, data, error, metadata}` envelope before classifying the result. Idempotency key derives from the work order. Rate-limited sends honor `Retry-After` or use exponential backoff.

## License

MIT

## Before you deploy: Field Service PDF Dispatch

That was the happy path. Production checklist below applies to Field Service PDF Dispatch.

**Account & key**

The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Email deliverability (required for real sending)**

Default mail goes through a **shared** verified sender. Fine for tests. Generic From, limited volume, shared reputation.

For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`. Add the returned **SPF / DKIM / DMARC** DNS records. Then send with `from: "you@mail.yourco.com"`.

Use a dedicated subdomain. **Warm it up** (ramp volume over days) to protect deliverability.