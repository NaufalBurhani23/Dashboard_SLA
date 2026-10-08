"""Dashboard aggregation helpers for SLA 1/SLA 2."""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.sla_record import SLARecord


def _period_query(db: Session, start_date=None, end_date=None):
    q = db.query(SLARecord).filter(SLARecord.sla_code == "SLA 1")
    if start_date:
        q = q.filter(SLARecord.registration_timestamp >= start_date)
    if end_date:
        q = q.filter(SLARecord.registration_timestamp <= end_date + " 23:59:59")
    return q


def _result_expr(sla: str):
    """Return a normalized Yes/No/N/A SQL expression for dashboard metrics.

    SLA 1 stores its final dashboard status as ON TIME / OUT OF DATE /
    INCOMPLETE, while SLA 2 stores Yes / No / N/A.  Normalize both here so
    all downstream aggregation (summary, per-unit, and trend) uses the same
    semantic status values without changing the stored SLA 1 result.
    """
    if sla == "SLA 1":
        return case(
            (SLARecord.status.in_(["ON TIME", "Yes"]), "Yes"),
            (SLARecord.status.in_(["OUT OF DATE", "No"]), "No"),
            (SLARecord.status.in_(["INCOMPLETE", "N/A"]), "N/A"),
            else_=SLARecord.status,
        )
    return case(
        (SLARecord.sla2_final_result.in_(["Yes", "ON TIME"]), "Yes"),
        (SLARecord.sla2_final_result.in_(["No", "OUT OF DATE"]), "No"),
        (SLARecord.sla2_final_result.in_(["N/A", "INCOMPLETE"]), "N/A"),
        else_=SLARecord.sla2_final_result,
    )


def _summary(q, result_col):
    row = q.with_entities(
        func.count(SLARecord.id).label("total"),
        func.sum(case((result_col == "Yes", 1), else_=0)).label("on_time"),
        func.sum(case((result_col == "No", 1), else_=0)).label("out_of_date"),
        func.sum(case((result_col == "N/A", 1), else_=0)).label("incomplete"),
    ).first()
    total = int(row.total or 0)
    yes = int(row.on_time or 0)
    no = int(row.out_of_date or 0)
    na = int(row.incomplete or 0)
    return {
        "total_records": total,
        "denominator": total,
        "on_time": yes,
        "out_of_date": no,
        "incomplete": na,
        "percentage": round(yes / total * 100, 2) if total else 0.0,
        "ontime_pct": round(yes / total * 100, 2) if total else 0.0,
        "ood_pct": round(no / total * 100, 2) if total else 0.0,
        "inc_pct": round(na / total * 100, 2) if total else 0.0,
    }


def _unit_rows(q, result_col, table_unit=None):
    if table_unit:
        q = q.filter(SLARecord.unit == table_unit)
    rows = q.with_entities(
        SLARecord.unit.label("unit"),
        func.count(SLARecord.id).label("total"),
        func.sum(case((result_col == "Yes", 1), else_=0)).label("on_time"),
        func.sum(case((result_col == "No", 1), else_=0)).label("out_of_date"),
        func.sum(case((result_col == "N/A", 1), else_=0)).label("incomplete"),
    ).group_by(SLARecord.unit).all()
    out = []
    for r in rows:
        total = int(r.total or 0)
        yes = int(r.on_time or 0)
        no = int(r.out_of_date or 0)
        na = int(r.incomplete or 0)
        pct = round(yes / total * 100, 2) if total else 0.0
        out.append({
            "unit": r.unit or "Tanpa Unit",
            "total": total,
            "denominator": total,
            "on_time": yes,
            "out_of_date": no,
            "late": no,
            "incomplete": na,
            "percentage": pct,
            "tindak_lanjut": "Pertahankan capaian." if pct >= 100 else "Evaluasi berkas yang belum memenuhi SLA.",
        })
    return sorted(out, key=lambda x: (x["percentage"], x["total"]), reverse=True)


def _trend(q, result_col):
    q = q.filter(SLARecord.registration_timestamp.isnot(None))
    rows = q.with_entities(
        func.date(SLARecord.registration_timestamp).label("tanggal"),
        func.count(SLARecord.id).label("jumlah_arsip"),
        func.sum(case((result_col == "Yes", 1), else_=0)).label("jumlah_berhasil"),
    ).group_by("tanggal").order_by("tanggal").all()
    return [{
        "tanggal": r.tanggal,
        "jumlah_arsip": int(r.jumlah_arsip or 0),
        "jumlah_berhasil": int(r.jumlah_berhasil or 0),
        "persentase": round((r.jumlah_berhasil or 0) / r.jumlah_arsip * 100, 2) if r.jumlah_arsip else None,
    } for r in rows]


def build_dashboard(db: Session, start_date=None, end_date=None, sla="ALL", table_unit=None, trend_unit=None):
    base = _period_query(db, start_date, end_date)
    units = sorted([x[0] for x in base.with_entities(SLARecord.unit).distinct().all() if x[0]])
    selected = sla.upper().replace(" ", "")
    selected_sla = "ALL" if selected in ("ALL", "SEMUA", "SEMUA SLA") else ("SLA 1" if selected in ("SLA1",) else "SLA 2")

    summaries = {}
    tables = {}
    rankings = {}
    trends = {}
    for code in ("SLA 1", "SLA 2"):
        result_col = _result_expr(code)
        q = base
        summaries[code] = _summary(q, result_col)
        tables[code] = _unit_rows(q, result_col, table_unit)
        rankings[code] = {
            "top5": tables[code][:5],
            "bottom5": sorted(tables[code], key=lambda x: (x["percentage"], -x["total"]))[:5],
        }
        tq = q.filter(SLARecord.unit == trend_unit) if trend_unit else q
        trends[code] = _trend(tq, result_col)

    if selected_sla == "ALL":
        s1 = {x["unit"]: x for x in tables["SLA 1"]}
        s2 = {x["unit"]: x for x in tables["SLA 2"]}
        if table_unit:
            unit_names = [table_unit]
        else:
            unit_names = sorted(set(s1) | set(s2))
        table = []
        for name in unit_names:
            a, b = s1.get(name), s2.get(name)
            table.append({
                "unit": name,
                "sla1": a or {"total": 0, "on_time": 0, "out_of_date": 0, "incomplete": 0, "percentage": 0},
                "sla2": b or {"total": 0, "on_time": 0, "out_of_date": 0, "incomplete": 0, "percentage": 0},
            })
        trend_sla = "SLA 1"
    else:
        table = tables[selected_sla]
        trend_sla = selected_sla

    return {
        "selected_sla": selected_sla,
        "available_units": units,
        "summaries": summaries,
        "unit_table": table,
        "ranking": rankings[trend_sla],
        "rankings": rankings,
        "trend": trends[trend_sla],
        "trends": trends,
        "trend_sla": trend_sla,
    }
