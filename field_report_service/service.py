from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmail, InfraiError
from .report_delivery import DeliveryResult, ReportRequest, deliver_follow_up


app = FastAPI(title="Field report delivery")


@app.post("/work-orders/report", response_model=DeliveryResult)
def send_work_order_report(order: ReportRequest) -> DeliveryResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    try:
        return deliver_follow_up(order, InfraiEmail(api_key))
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
