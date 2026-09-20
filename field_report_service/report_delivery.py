from __future__ import annotations

import base64
import html
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class WorkOrderPhoto(BaseModel):
    caption: str = Field(min_length=1, max_length=120)
    captured_at: str = Field(min_length=1, max_length=40)


class ReportRequest(BaseModel):
    work_order_id: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=120)
    technician_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    dispatch_status: str = Field(pattern="^(scheduled|dispatched|on_site|completed)$")
    follow_up_required: bool
    follow_up_note: str = Field(min_length=1, max_length=500)
    photos: list[WorkOrderPhoto] = Field(min_length=1, max_length=12)


class DeliveryResult(BaseModel):
    sent: bool
    reason: str
    message_id: str | None = None


class EmailSender(Protocol):
    def send(
        self, *, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, object]:
        raise AssertionError("EmailSender.send must be provided by the delivery adapter")


@dataclass(frozen=True)
class FieldReport:
    filename: str
    pdf_bytes: bytes


def should_send_report(order: ReportRequest) -> tuple[bool, str]:
    if order.dispatch_status not in {"dispatched", "on_site", "completed"}:
        return False, "work order has not been dispatched"
    if not order.follow_up_required:
        return False, "technician follow-up is not required"
    return True, "follow-up report sent"


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(order: ReportRequest) -> FieldReport:
    lines = [
        f"Work order {order.work_order_id}",
        f"Customer: {order.customer_name}",
        f"Dispatch status: {order.dispatch_status}",
        f"Follow-up: {order.follow_up_note}",
        "Photos:",
    ]
    lines.extend(f"- {photo.caption} ({photo.captured_at})" for photo in order.photos)
    drawing = ["BT", "/F1 11 Tf", "54 760 Td"]
    for index, line in enumerate(lines):
        if index:
            drawing.append("0 -18 Td")
        drawing.append(f"({_pdf_escape(line)}) Tj")
    drawing.append("ET")
    stream = "\n".join(drawing).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return FieldReport(f"work-order-{order.work_order_id}.pdf", bytes(pdf))


def deliver_follow_up(order: ReportRequest, sender: EmailSender) -> DeliveryResult:
    should_send, reason = should_send_report(order)
    if not should_send:
        return DeliveryResult(sent=False, reason=reason)

    report = build_pdf(order)
    encoded = base64.b64encode(report.pdf_bytes).decode("ascii")
    download_href = f"data:application/pdf;base64,{encoded}"
    body = (
        f"<p>Work order <strong>{html.escape(order.work_order_id)}</strong> needs follow-up.</p>"
        f'<p><a download="{html.escape(report.filename)}" href="{download_href}">Download PDF report</a></p>'
    )
    response = sender.send(
        to=str(order.technician_email),
        subject=f"Follow-up report: work order {order.work_order_id}",
        html=body,
        idempotency_key=f"field-report-{order.work_order_id}",
    )
    return DeliveryResult(
        sent=True, reason=reason, message_id=str(response["message_id"])
    )
