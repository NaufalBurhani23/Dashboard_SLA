from datetime import date
from app.sla.sla3.calculator import SLA3Calculator


def _ctx():
    return {
        "h5": date(2026, 8, 31),
        "h6": date(2026, 8, 28),
        "h8": date(2026, 7, 31),
        "h9": date(2026, 7, 30),
        "holidays": [],
    }


def test_sla3a_checks_x_and_ad_before_aj_short_circuit():
    row = {
        "format_arsip": "Fisik",
        "document_type": "Inaktif",
        "tanggal_registrasi": date(2026, 8, 3),
        "tanggal_penjadwalan_inaktif": None,
        "jam_penjadwalan_inaktif": None,
        "tanggal_jadwal_penjemputan": date(2026, 8, 4),
        "tanggal_penjadwalan_inaktif_2": date(2026, 8, 5),
        "unit": "UID JABAR",
    }
    result = SLA3Calculator.evaluate_sla_3a(row, _ctx())
    assert result["result"] == "N/A"


def test_latest_sla3_manual_rules_exclude_ditolak_command_center():
    from app.sla.sla3.manual_rules import apply_sla3_manual_check

    row = {
        "sumber": "ELARCH",
        "status_registrasi": "Ditolak Command Center (Revisi)",
        "status_inisiasi": "-",
        "posisi_data": "",
        "format_arsip": "Fisik",
        "document_type": "Inaktif",
        "tanggal_registrasi": date(2026, 8, 3),
        "tanggal_penjadwalan_inaktif": date(2026, 8, 4),
        "jam_penjadwalan_inaktif": "10:00:00",
    }
    result = apply_sla3_manual_check(row, _ctx())
    assert result["result"] == "N/A"
