from __future__ import annotations

from datetime import date, datetime, time, timedelta
import io
import json
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from app.database import get_db
from app.models.holiday import HolidayCalendar
from app.models.sla4_record import SLA4Record
from app.models.unit_area import UnitArea
from app.services.holiday_service import (
    active_rows,
    write_version,
    delete_holiday as service_delete_holiday,
    edit_holiday as service_edit_holiday,
    holidays_for_range,
    latest_version,
    add_holiday as service_add_holiday,
)
from app.services.excel_parser import parse_registrasi_sheet, _as_date as as_date
from app.sla.sla4.unit_area_service import find_unit, normalize_unit, seed_default_units, target_days
from app.sla.sla4.calculator import SLA4Calculator

router = APIRouter(prefix="/sla4", tags=["SLA 4"])


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "aktif"}


@router.get("/health")
def health():
    return {"status": "ok", "scope": "SLA 4A + SLA 4B"}


@router.get("/units")
def list_units(
    active_only: bool = True,
    effective_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(UnitArea)
    if active_only:
        q = q.filter(UnitArea.active.is_(True))
    rows = q.order_by(UnitArea.unit_type, UnitArea.kawasan, UnitArea.unit_name).all()
    if effective_date:
        rows = [
            row
            for row in rows
            if (row.valid_from is None or row.valid_from <= effective_date)
            and (row.valid_to is None or row.valid_to >= effective_date)
        ]
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "unit_name": row.unit_name,
                "unit_type": row.unit_type,
                "kawasan": row.kawasan,
                "target_days": target_days(row.kawasan),
                "active": row.active,
                "valid_from": row.valid_from.isoformat() if row.valid_from else None,
                "valid_to": row.valid_to.isoformat() if row.valid_to else None,
            }
            for row in rows
        ],
    }


@router.post("/units")
def create_unit(payload: dict, db: Session = Depends(get_db)):
    name = str(payload.get("unit_name") or "").strip()
    unit_type = str(payload.get("unit_type") or "Pendukung").strip()
    kawasan = str(payload.get("kawasan") or "Dalam Kawasan").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nama unit wajib diisi.")
    if unit_type not in {"Pusat", "Pendukung"}:
        raise HTTPException(status_code=400, detail="Jenis unit harus Pusat atau Pendukung.")
    if kawasan not in {"Dalam Kawasan", "Luar Kawasan"}:
        raise HTTPException(status_code=400, detail="Kawasan harus Dalam Kawasan atau Luar Kawasan.")
    valid_from = as_date(payload.get("valid_from"))
    valid_to = as_date(payload.get("valid_to"))
    if valid_from and valid_to and valid_from > valid_to:
        raise HTTPException(status_code=400, detail="Valid From tidak boleh melewati Valid To.")
    normalized = normalize_unit(name)
    duplicate = db.query(UnitArea).filter(
        UnitArea.unit_name_normalized == normalized,
        UnitArea.valid_from == valid_from,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Mapping unit dengan periode mulai tersebut sudah ada.")

    row = UnitArea(
        unit_name=name,
        unit_name_normalized=normalized,
        unit_type=unit_type,
        kawasan=kawasan,
        active=_parse_bool(payload.get("active", True)),
        valid_from=valid_from,
        valid_to=valid_to,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"message": "Master unit SLA 4 berhasil ditambahkan.", "id": row.id}


@router.put("/units/{unit_id}")
def update_unit(unit_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(UnitArea).filter(UnitArea.id == unit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Mapping unit tidak ditemukan.")
    name = str(payload.get("unit_name") or row.unit_name).strip()
    unit_type = str(payload.get("unit_type") or row.unit_type).strip()
    kawasan = str(payload.get("kawasan") or row.kawasan).strip()
    valid_from = as_date(payload.get("valid_from")) if payload.get("valid_from") is not None else row.valid_from
    valid_to = as_date(payload.get("valid_to")) if payload.get("valid_to") is not None else row.valid_to
    if unit_type not in {"Pusat", "Pendukung"} or kawasan not in {"Dalam Kawasan", "Luar Kawasan"}:
        raise HTTPException(status_code=400, detail="Nilai jenis unit/kawasan tidak valid.")
    if valid_from and valid_to and valid_from > valid_to:
        raise HTTPException(status_code=400, detail="Valid From tidak boleh melewati Valid To.")

    duplicate = (
        db.query(UnitArea)
        .filter(UnitArea.unit_name_normalized == normalize_unit(name), UnitArea.valid_from == valid_from, UnitArea.id != unit_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Mapping unit dengan periode mulai tersebut sudah ada.")

    row.unit_name = name
    row.unit_name_normalized = normalize_unit(name)
    row.unit_type = unit_type
    row.kawasan = kawasan
    if payload.get("active") is not None:
        row.active = _parse_bool(payload.get("active"))
    row.valid_from = valid_from
    row.valid_to = valid_to
    db.commit()
    return {"message": "Master unit SLA 4 berhasil diperbarui."}


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    row = db.query(UnitArea).filter(UnitArea.id == unit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Mapping unit tidak ditemukan.")
    db.delete(row)
    db.commit()
    return {"message": "Mapping unit SLA 4 dihapus."}


@router.post("/units/seed-defaults")
def seed_units(db: Session = Depends(get_db)):
    inserted = seed_default_units(db)
    return {"inserted": inserted, "message": f"{inserted} mapping default dimasukkan."}


# ---------------- Holiday Calendar ----------------

@router.get("/holidays")
def list_holidays(year: int = 2026, db: Session = Depends(get_db)):
    version = latest_version(db, year)
    rows = active_rows(db, year)
    return {
        "year": year,
        "version": version,
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "date": row.holiday_date.isoformat(),
                "description": row.description or "",
                "version": row.version,
            }
            for row in rows
        ],
    }


@router.post("/holidays")
def create_holiday(payload: dict, db: Session = Depends(get_db)):
    try:
        d = date.fromisoformat(str(payload["date"]))
        version = service_add_holiday(db, d, str(payload.get("description") or ""))
        db.commit()
        return {"message": "Hari libur ditambahkan sebagai versi kalender baru.", "version": version}
    except (KeyError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400 if isinstance(exc, KeyError) else 409, detail=str(exc))


@router.put("/holidays/{holiday_id}")
def update_holiday(holiday_id: int, payload: dict, db: Session = Depends(get_db)):
    try:
        d = date.fromisoformat(str(payload["date"]))
        version = service_edit_holiday(db, holiday_id, d, str(payload.get("description") or ""))
        db.commit()
        return {"message": "Hari libur diperbarui sebagai versi kalender baru.", "version": version}
    except (KeyError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400 if isinstance(exc, KeyError) else 409, detail=str(exc))


@router.delete("/holidays/{holiday_id}")
def remove_holiday(holiday_id: int, db: Session = Depends(get_db)):
    try:
        version = service_delete_holiday(db, holiday_id)
        db.commit()
        return {"message": "Hari libur dihapus dari kalender aktif.", "version": version}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))



@router.post("/holidays/import")
async def import_holidays(file: UploadFile = File(...), year: int = 2026, db: Session = Depends(get_db)):
    """Import holiday dates from a simple table or vendor Reference List C3:C20."""
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        parsed: list[tuple[date, str]] = []
        for ws in wb.worksheets:
            values = list(ws.iter_rows(values_only=True))
            if not values:
                continue
            header = [str(v or "").strip().lower() for v in values[0]]
            date_idx = next((i for i, h in enumerate(header) if h in {"tanggal", "date", "holiday", "hari libur", "holiday date"}), None)
            desc_idx = next((i for i, h in enumerate(header) if h in {"keterangan", "description", "holiday name", "nama hari libur"}), None)
            if date_idx is not None:
                for row in values[1:]:
                    if date_idx >= len(row):
                        continue
                    d = as_date(row[date_idx])
                    if d and d.year == year:
                        desc = str(row[desc_idx] or "") if desc_idx is not None and desc_idx < len(row) else ""
                        parsed.append((d, desc))
                if parsed:
                    break
        if not parsed:
            ref = wb["99. Reference List"] if "99. Reference List" in wb.sheetnames else wb[wb.sheetnames[0]]
            for row_num in range(3, 21):
                d = as_date(ref[f"C{row_num}"].value)
                if d and d.year == year:
                    parsed.append((d, str(ref[f"B{row_num}"].value or "Reference List")))
        wb.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Gagal membaca daftar hari libur: {exc}")

    parsed = list(dict.fromkeys(parsed))
    if not parsed:
        raise HTTPException(status_code=400, detail="Tidak menemukan tanggal hari libur yang sesuai tahun.")

    current = [(row.holiday_date, row.description or "") for row in active_rows(db, year)]
    merged = {(d, desc) for d, desc in current}
    merged.update(parsed)
    version = write_version(db, year, merged)
    db.commit()
    return {"message": f"{len(parsed)} tanggal diproses dan kalender aktif dibuat ulang.", "year": year, "version": version, "count": len(merged)}

@router.get("/holidays/preview")
def preview_holidays(start_date: date, end_date: date, db: Session = Depends(get_db)):
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    holidays, versions = holidays_for_range(db, start_date, end_date)
    holiday_set = set(holidays)
    days = []
    cursor = start_date
    networkdays = 0
    while cursor <= end_date:
        if cursor.weekday() >= 5:
            reason = "Akhir pekan"
            working = False
        elif cursor in holiday_set:
            reason = "Hari libur"
            working = False
        else:
            reason = "Hari kerja"
            working = True
            networkdays += 1
        days.append({"date": cursor.isoformat(), "is_working_day": working, "reason": reason})
        cursor += timedelta(days=1)
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "networkdays": networkdays,
        "networkdays_minus_one": networkdays - 1,
        "calendar_versions": versions,
        "days": days,
    }


# ---------------- SLA 4 Calculation ----------------

@router.post("/import")
async def import_sla4(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        records, parser_context = parse_registrasi_sheet(content, holidays=[])
        period = parser_context["period_label"]
        parser_info = {
            "sheet": "shared registration parser (SLA 1/SLA 2)",
            "header_row": None,
            "header_mapping": None,
            "record_count": len(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Gagal membaca raw Excel untuk SLA 4: {exc}")
    if not records:
        raise HTTPException(status_code=400, detail="Tidak ada record raw yang dapat diproses untuk SLA 4.")

    # Re-import the same reporting period so the SLA 4 table never duplicates the dataset.
    db.query(SLA4Record).filter(SLA4Record.reporting_period == period).delete(synchronize_session=False)
    db.commit()

    # Load the latest holiday calendars once for the entire dataset. The range
    # includes the previous month because SLA 4 period-gate reference days use
    # the last working days of the previous month.
    all_dates = []
    for item in records:
        for key in (
            "tanggal_registrasi",
            "tanggal_jadwal_penjemputan",
            "tanggal_penjemputan_dokumen",
            "tanggal_gagal_penjemputan",
            "tanggal_penolakan_jadwal_penjemputan",
            "tanggal_penjadwalan_inaktif_2",
            "tanggal_runner_record_center",
        ):
            if item.get(key):
                all_dates.append(item[key])
    range_end = max(all_dates) if all_dates else date.today()
    period_start = date(range_end.year, range_end.month, 1)
    range_start = period_start - timedelta(days=1)
    holidays, calendar_versions = holidays_for_range(db, range_start, range_end)

    # Load the master unit table once rather than querying it for every raw row.
    unit_rows = db.query(UnitArea).filter(UnitArea.active.is_(True)).order_by(UnitArea.valid_from.desc().nullslast(), UnitArea.id.desc()).all()

    def resolve_unit(unit_name: str | None, basis_date: date | None):
        normalized = normalize_unit(unit_name)
        candidates = [row for row in unit_rows if row.unit_name_normalized == normalized]
        if basis_date:
            candidates = [
                row
                for row in candidates
                if (row.valid_from is None or row.valid_from <= basis_date)
                and (row.valid_to is None or row.valid_to >= basis_date)
            ]
        return candidates[0] if candidates else None

    counters = {"Yes": 0, "No": 0, "N/A": 0}
    a_counts = {"Yes": 0, "No": 0, "N/A": 0}
    b_counts = {"Yes": 0, "No": 0, "N/A": 0}
    unit_missing = 0

    for item in records:
        schedule = item.get("tanggal_jadwal_penjemputan")
        pickup = item.get("tanggal_penjemputan_dokumen")
        basis_date = schedule or item.get("tanggal_registrasi")
        unit_row = resolve_unit(item.get("unit"), basis_date)
        area = unit_row.kawasan if unit_row else None
        unit_type = unit_row.unit_type if unit_row else None
        if unit_row is None:
            unit_missing += 1

        evaluation = SLA4Calculator.evaluate(item, holidays, area)
        result = evaluation["sla4_final_result"]
        counters[result] += 1
        a_counts[evaluation["sla4a_result"]] += 1
        b_counts[evaluation["sla4b_result"]] += 1

        db.add(
            SLA4Record(
                import_file_name=file.filename,
                reporting_period=period,
                nomor_registrasi=item.get("nomor_registrasi"),
                nama_dokumen=item.get("nama_dokumen"),
                unit=item.get("unit") or "Tanpa Unit",
                unit_type=unit_type,
                kawasan=area,
                sumber=item.get("sumber"),
                status_registrasi=item.get("status_registrasi"),
                status_inisiasi=item.get("status_inisiasi"),
                posisi_data=item.get("posisi_data"),
                format_arsip=item.get("format_arsip"),
                document_type=item.get("document_type"),
                tanggal_registrasi=item.get("tanggal_registrasi"),
                jam_registrasi=str(item.get("jam_registrasi")) if item.get("jam_registrasi") else None,
                tanggal_verifikasi_arsip=item.get("tanggal_verifikasi_arsip"),
                jam_verifikasi_arsip=str(item.get("jam_verifikasi_arsip")) if item.get("jam_verifikasi_arsip") else None,
                tanggal_penjadwalan_inaktif=item.get("tanggal_penjadwalan_inaktif"),
                jam_penjadwalan_inaktif=str(item.get("jam_penjadwalan_inaktif")) if item.get("jam_penjadwalan_inaktif") else None,
                tanggal_jadwal_penjemputan=item.get("tanggal_jadwal_penjemputan"),
                jam_jadwal_penjemputan=str(item.get("jam_jadwal_penjemputan")) if item.get("jam_jadwal_penjemputan") else None,
                tanggal_penolakan_jadwal_penjemputan=item.get("tanggal_penolakan_jadwal_penjemputan"),
                jam_penolakan_jadwal_penjemputan=str(item.get("jam_penolakan_jadwal_penjemputan")) if item.get("jam_penolakan_jadwal_penjemputan") else None,
                tanggal_gagal_penjemputan=item.get("tanggal_gagal_penjemputan"),
                jam_gagal_penjemputan=str(item.get("jam_gagal_penjemputan")) if item.get("jam_gagal_penjemputan") else None,
                tanggal_penjadwalan_inaktif_2=item.get("tanggal_penjadwalan_inaktif_2"),
                jam_penjadwalan_inaktif_2=str(item.get("jam_penjadwalan_inaktif_2")) if item.get("jam_penjadwalan_inaktif_2") else None,
                tanggal_penjemputan_dokumen=item.get("tanggal_penjemputan_dokumen"),
                jam_penjemputan_dokumen=str(item.get("jam_penjemputan_dokumen")) if item.get("jam_penjemputan_dokumen") else None,
                tanggal_runner_record_center=item.get("tanggal_runner_record_center"),
                jam_runner_record_center=str(item.get("jam_runner_record_center")) if item.get("jam_runner_record_center") else None,
                sla4a_result=evaluation["sla4a_result"],
                sla4a_working_days=evaluation["sla4a_working_days"],
                sla4a_start_field=evaluation["sla4a_start_field"],
                sla4a_end_field=evaluation["sla4a_end_field"],
                sla4a_reason=evaluation["sla4a_reason"],
                sla4b_result=evaluation["sla4b_result"],
                sla4b_working_days=evaluation["sla4b_working_days"],
                sla4b_start_field=evaluation["sla4b_start_field"],
                sla4b_end_field=evaluation["sla4b_end_field"],
                sla4b_reason=evaluation["sla4b_reason"],
                sla4_final_result=evaluation["sla4_final_result"],
                sla4_decision_source=evaluation["sla4_decision_source"],
                sla4_manual_result=evaluation["sla4_manual_result"],
                sla4_reason=evaluation["sla4_reason"],
                sla4_target_days=evaluation["sla4_target_days"],
                sla4_anomaly=evaluation["sla4_anomaly"],
                holiday_calendar_versions=json.dumps(calendar_versions, ensure_ascii=False),
            )
        )
    db.commit()

    return {
        "message": f"Berhasil menghitung SLA 4A + SLA 4B untuk {len(records)} record periode {period}.",
        "records": len(records),
        "period": period,
        "file_name": file.filename,
        "final": counters,
        "sla4a": a_counts,
        "sla4b": b_counts,
        "unit_mapping_missing": unit_missing,
        "parser": parser_info,
    }


def _apply_sla4_dashboard_filters(query, start_date: Optional[str], end_date: Optional[str], unit: Optional[str] = None):
    if start_date:
        try:
            query = query.filter(SLA4Record.tanggal_registrasi >= date.fromisoformat(start_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format start_date harus YYYY-MM-DD.")
    if end_date:
        try:
            query = query.filter(SLA4Record.tanggal_registrasi <= date.fromisoformat(end_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Format end_date harus YYYY-MM-DD.")
    if unit:
        query = query.filter(SLA4Record.unit == unit)
    return query


def _sla4_unit_summary(rows):
    grouped = {}
    for row in rows:
        name = row.unit or "Tanpa Unit"
        item = grouped.setdefault(name, {"unit": name, "total": 0, "on_time": 0, "out_of_date": 0, "incomplete": 0})
        item["total"] += 1
        if row.sla4_final_result == "Yes":
            item["on_time"] += 1
        elif row.sla4_final_result == "No":
            item["out_of_date"] += 1
        else:
            item["incomplete"] += 1

    result = []
    for item in grouped.values():
        # Dashboard denominator follows the same convention as SLA 1/SLA 2:
        # every imported record is part of the denominator, including N/A.
        # Therefore the KPI is On Time / Total Records.
        denominator = item["total"]
        pct = round(item["on_time"] / denominator * 100, 2) if denominator else 0.0
        item.update({
            "denominator": denominator,
            "percentage": pct,
            "late": item["out_of_date"],
            "tindak_lanjut": "Pertahankan capaian." if denominator and pct >= 100 else "Evaluasi berkas yang belum memenuhi SLA.",
        })
        result.append(item)
    return sorted(result, key=lambda x: (x["percentage"], x["denominator"], x["total"]), reverse=True)


@router.get("/dashboard")
def sla4_dashboard(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    table_unit: Optional[str] = None,
    trend_unit: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Dashboard payload using the same visual information architecture as SLA 1/SLA 2."""
    base = _apply_sla4_dashboard_filters(db.query(SLA4Record), start_date, end_date)
    all_rows = base.order_by(SLA4Record.id).all()
    total = len(all_rows)
    yes = sum(1 for row in all_rows if row.sla4_final_result == "Yes")
    no = sum(1 for row in all_rows if row.sla4_final_result == "No")
    na = total - yes - no
    # Denominator is ALL records, including N/A, consistent with SLA 1/SLA 2.
    denominator = total
    summary = {
        "total_records": total,
        "denominator": denominator,
        "on_time": yes,
        "out_of_date": no,
        "incomplete": na,
        "percentage": round(yes / denominator * 100, 2) if denominator else 0.0,
        "ontime_pct": round(yes / denominator * 100, 2) if denominator else 0.0,
        "ood_pct": round(no / denominator * 100, 2) if denominator else 0.0,
        "inc_pct": round(na / total * 100, 2) if total else 0.0,
    }

    table_rows = [r for r in all_rows if not table_unit or r.unit == table_unit]
    unit_table = _sla4_unit_summary(table_rows)
    rankings = {
        "top5": unit_table[:5],
        "bottom5": sorted(unit_table, key=lambda x: (x["percentage"], -x["denominator"], -x["total"]))[:5],
    }

    trend_rows = [r for r in all_rows if not trend_unit or r.unit == trend_unit]
    trend_map = {}
    for row in trend_rows:
        if not row.tanggal_registrasi:
            continue
        key = row.tanggal_registrasi.isoformat()
        item = trend_map.setdefault(key, {"tanggal": key, "jumlah_arsip": 0, "jumlah_berhasil": 0})
        item["jumlah_arsip"] += 1
        if row.sla4_final_result == "Yes":
            item["jumlah_berhasil"] += 1
    trend = []
    for key in sorted(trend_map):
        item = trend_map[key]
        item["persentase"] = round(item["jumlah_berhasil"] / item["jumlah_arsip"] * 100, 2) if item["jumlah_arsip"] else None
        trend.append(item)

    units = sorted({r.unit for r in all_rows if r.unit})
    return {
        "selected_sla": "SLA 4",
        "available_units": units,
        "summary": summary,
        "unit_table": unit_table,
        "ranking": rankings,
        "trend": trend,
    }


@router.get("/summary")
def sla4_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(SLA4Record.id)).scalar() or 0
    yes = db.query(func.count(SLA4Record.id)).filter(SLA4Record.sla4_final_result == "Yes").scalar() or 0
    no = db.query(func.count(SLA4Record.id)).filter(SLA4Record.sla4_final_result == "No").scalar() or 0
    na = db.query(func.count(SLA4Record.id)).filter(SLA4Record.sla4_final_result == "N/A").scalar() or 0
    # Keep the summary denominator equal to the complete record population.
    denominator = total
    return {
        "total": total,
        "yes": yes,
        "no": no,
        "na": na,
        "denominator": denominator,
        "percentage": round((yes / denominator) * 100, 2) if denominator else 0,
    }


@router.get("/records")
def sla4_records(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    result: Optional[str] = None,
    unit: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SLA4Record)
    if result:
        q = q.filter(SLA4Record.sla4_final_result == result)
    if unit:
        q = q.filter(SLA4Record.unit.ilike(f"%{unit}%"))
    total = q.count()
    rows = q.order_by(SLA4Record.id).offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "data": [
            {
                "id": row.id,
                "nomor_registrasi": row.nomor_registrasi,
                "unit": row.unit,
                "unit_type": row.unit_type,
                "kawasan": row.kawasan,
                "sumber": row.sumber,
                "status_registrasi": row.status_registrasi,
                "format_arsip": row.format_arsip,
                "document_type": row.document_type,
                "tanggal_registrasi": row.tanggal_registrasi.isoformat() if row.tanggal_registrasi else None,
                "tanggal_jadwal_penjemputan": row.tanggal_jadwal_penjemputan.isoformat() if row.tanggal_jadwal_penjemputan else None,
                "tanggal_penjemputan_dokumen": row.tanggal_penjemputan_dokumen.isoformat() if row.tanggal_penjemputan_dokumen else None,
                "sla4a_result": row.sla4a_result,
                "sla4a_working_days": row.sla4a_working_days,
                "sla4a_reason": row.sla4a_reason,
                "sla4b_result": row.sla4b_result,
                "sla4b_working_days": row.sla4b_working_days,
                "sla4b_reason": row.sla4b_reason,
                "sla4_final_result": row.sla4_final_result,
                "sla4_decision_source": row.sla4_decision_source,
                "sla4_reason": row.sla4_reason,
                "sla4_target_days": row.sla4_target_days,
                "sla4_anomaly": row.sla4_anomaly,
                "holiday_calendar_versions": json.loads(row.holiday_calendar_versions or "{}"),
            }
            for row in rows
        ],
    }
