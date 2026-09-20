from __future__ import annotations

import os

from field_report_service.infrai_email import InfraiEmail
from field_report_service.report_delivery import ReportRequest, deliver_follow_up


recipient = os.environ.get("REPORT_RECIPIENT")
api_key = os.environ.get("INFRAI_API_KEY")
if not recipient or not api_key:
    raise SystemExit("Set INFRAI_API_KEY and REPORT_RECIPIENT")

order = ReportRequest(
    work_order_id="WO-1842",
    customer_name="Northwind Bakery",
    technician_email=recipient,
    dispatch_status="on_site",
    follow_up_required=True,
    follow_up_note="Confirm compressor pressure after the replacement settles.",
    photos=[
        {"caption": "Replacement compressor installed", "captured_at": "2026-09-05T09:35:00Z"},
        {"caption": "Final gauge reading", "captured_at": "2026-09-05T10:10:00Z"},
    ],
)
result = deliver_follow_up(order, InfraiEmail(api_key))
print(f"sent={result.sent} message_id={result.message_id}")
