from datetime import date, time

from app.sla.sla4.calculator import SLA4Calculator


def base_row():
    return {
        "format_arsip": "Fisik",
        "document_type": "Inaktif",
        "tanggal_penjadwalan_inaktif": date(2026, 8, 10),
        "jam_penjadwalan_inaktif": time(9, 0),
        "tanggal_registrasi": date(2026, 8, 10),
        "tanggal_jadwal_penjemputan": date(2026, 8, 13),
        "jam_jadwal_penjemputan": time(9, 0),
        "tanggal_penjemputan_dokumen": date(2026, 8, 14),
        "jam_penjemputan_dokumen": time(10, 0),
        "tanggal_verifikasi_arsip": date(2026, 8, 13),
        "jam_verifikasi_arsip": time(8, 0),
        "tanggal_runner_record_center": date(2026, 8, 14),
        "jam_runner_record_center": time(11, 0),
    }


def test_sla4a_in_kawasan_h_plus_1():
    row = base_row()
    result = SLA4Calculator.evaluate_4a(row, [], 1)
    assert result["result"] == "Yes"
    assert result["working_days"] == 1


def test_sla4a_luar_kawasan_h_plus_2():
    row = base_row()
    row["tanggal_penjemputan_dokumen"] = date(2026, 8, 17)
    result = SLA4Calculator.evaluate_4a(row, [], 2)
    assert result["result"] == "Yes"
    assert result["working_days"] == 2


def test_sla4a_holiday_is_excluded():
    row = base_row()
    row["tanggal_penjemputan_dokumen"] = date(2026, 8, 17)
    result = SLA4Calculator.evaluate_4a(row, [date(2026, 8, 17)], 1)
    assert result["result"] == "Yes"
    assert result["working_days"] == 1


def test_sla4b_named_headers_use_rejection_to_reschedule_path():
    row = base_row()
    row.update(
        {
            "tanggal_penolakan_jadwal_penjemputan": date(2026, 8, 13),
            "jam_penolakan_jadwal_penjemputan": time(10, 0),
            "tanggal_penjadwalan_inaktif_2": date(2026, 8, 14),
            "jam_penjadwalan_inaktif_2": time(9, 0),
        }
    )
    result = SLA4Calculator.evaluate_4b(row, [])
    assert result["result"] == "Yes"
    assert "Penolakan" in result["start_field"]
    assert "Penjadwalan Arsip Inaktif 2" in result["end_field"]


def test_final_yes_when_either_4a_or_4b_yes():
    row = base_row()
    result = SLA4Calculator.evaluate(row, [], "Dalam Kawasan")
    assert result["sla4_final_result"] == "Yes"


def test_sla4_dashboard_percentage_uses_all_records_as_denominator():
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.sla4_record import SLA4Record
    from app.api.sla4_routes import sla4_dashboard

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()
    try:
        db.add_all([
            SLA4Record(unit="UNIT A", reporting_period="2026-08", tanggal_registrasi=date(2026, 8, 1), sla4_final_result="Yes"),
            SLA4Record(unit="UNIT A", reporting_period="2026-08", tanggal_registrasi=date(2026, 8, 2), sla4_final_result="No"),
            SLA4Record(unit="UNIT A", reporting_period="2026-08", tanggal_registrasi=date(2026, 8, 3), sla4_final_result="N/A"),
        ])
        db.commit()
        payload = sla4_dashboard(db=db)
        assert payload["summary"]["total_records"] == 3
        assert payload["summary"]["denominator"] == 3
        assert payload["summary"]["on_time"] == 1
        assert payload["summary"]["percentage"] == 33.33
        row = payload["unit_table"][0]
        assert row["total"] == 3
        assert row["denominator"] == 3
        assert row["on_time"] == 1
        assert row["percentage"] == 33.33
    finally:
        db.close()
