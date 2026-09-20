from field_report_service.report_delivery import ReportRequest, deliver_follow_up


class RecordingSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, **request: str) -> dict[str, object]:
        self.calls.append(request)
        return {"message_id": "msg_1842"}


def make_order(**changes: object) -> ReportRequest:
    values: dict[str, object] = {
        "work_order_id": "WO-1842",
        "customer_name": "Northwind Bakery",
        "technician_email": "tech@example.com",
        "dispatch_status": "on_site",
        "follow_up_required": True,
        "follow_up_note": "Recheck compressor pressure tomorrow.",
        "photos": [{"caption": "Installed compressor", "captured_at": "2026-09-05T09:35:00Z"}],
    }
    values.update(changes)
    return ReportRequest.model_validate(values)


def test_sends_pdf_download_for_dispatched_follow_up() -> None:
    sender = RecordingSender()

    result = deliver_follow_up(make_order(), sender)

    assert result.sent is True
    assert result.message_id == "msg_1842"
    assert sender.calls[0]["idempotency_key"] == "field-report-WO-1842"
    assert "data:application/pdf;base64," in sender.calls[0]["html"]


def test_keeps_scheduled_order_out_of_the_inbox() -> None:
    sender = RecordingSender()

    result = deliver_follow_up(make_order(dispatch_status="scheduled"), sender)

    assert result.sent is False
    assert result.reason == "work order has not been dispatched"
    assert sender.calls == []
