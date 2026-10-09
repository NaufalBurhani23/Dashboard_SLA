from __future__ import annotations

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.sla_record import SLARecord
from app.services.excel_parser import parse_registrasi_sheet
from app.sla.sla3.calculator import SLA3Calculator

router = APIRouter(prefix="/sla3", tags=["SLA 3"])

@router.get("/dashboard")
def get_sla3_dashboard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    trend_unit: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SLARecord).filter(SLARecord.sla_code == "SLA 3")
    if start_date:
        q = q.filter(SLARecord.registration_timestamp >= start_date)
    if end_date:
        q = q.filter(SLARecord.registration_timestamp <= end_date + " 23:59:59")
    
    records = q.all()
    total_records = len(records)
    
    on_time = sum(1 for r in records if r.status in ["ON TIME", "Yes"])
    # SLA 3 murni tidak memiliki status Out of Date (diset 0 sesuai master Excel)
    out_of_date = 0
    incomplete = total_records - on_time
    
    denominator = total_records
    percentage = round((on_time / denominator * 100), 2) if denominator > 0 else 0.0

    # Unit Table grouping
    unit_stats = {}
    for r in records:
        u = r.unit_name or "Unknown"
        if u not in unit_stats:
            unit_stats[u] = {"total": 0, "on_time": 0, "out_of_date": 0, "incomplete": 0}
        unit_stats[u]["total"] += 1
        if r.status in ["ON TIME", "Yes"]:
            unit_stats[u]["on_time"] += 1
        else:
            unit_stats[u]["incomplete"] += 1

    unit_table = []
    for u, st in unit_stats.items():
        total_u = st["total"]
        pct = round((st["on_time"] / total_u * 100), 2) if total_u > 0 else 0.0
        unit_table.append({
            "unit": u,
            "total": total_u,
            "denominator": total_u,
            "on_time": st["on_time"],
            "out_of_date": 0,
            "incomplete": total_u - st["on_time"],
            "percentage": pct
        })

    return {
        "summary": {
            "total_records": total_records,
            "denominator": denominator,
            "on_time": on_time,
            "out_of_date": out_of_date,
            "incomplete": incomplete,
            "percentage": percentage,
            "ontime_pct": percentage,
            "ood_pct": 0.0,
            "inc_pct": round((incomplete / total_records * 100), 2) if total_records > 0 else 0.0,
        },
        "unit_table": unit_table,
        "ranking": {"top5": [], "bottom5": []},
        "trend": [],
        "available_units": sorted(list(unit_stats.keys()))
    }