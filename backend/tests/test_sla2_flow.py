from datetime import date, time

import pytest

from app.sla.sla2.calculator import SLA2Calculator
from app.sla.sla2.manual_rules import apply_sla2a_manual_check, apply_sla2b_manual_check


CTX = {
    # August 2026 period gate from the vendor workbook.
    "h5": date(2026, 8, 31),  # Hari Kerja Terakhir Hari ke-1 Bulan Berjalan
    "h6": date(2026, 8, 28),  # Hari Kerja Terakhir Hari ke-2 Bulan Berjalan
    "h8": date(2026, 7, 31),  # Hari Kerja Terakhir Hari ke-1 Bulan Sebelumnya
    "h9": date(2026, 7, 30),  # Hari Kerja Terakhir Hari ke-2 Bulan Sebelumnya
    "holidays": [],
    "sla2_cutoff": time(10, 0),
}


def base(**overrides):
    """Build a mapped raw row using business header names, not Excel letters."""
    row = {
        "sumber": "ELARCH",
        "status_registrasi": "Diarsipkan",
        "status_inisiasi": "-",
        "posisi_data": "Record Center",
        "format_arsip": "Fisik",
        "document_type": "Inaktif",
        "tanggal_registrasi": date(2026, 8, 20),
        "jam_registrasi": time(9, 0),
        "tanggal_verifikasi_uf": None,
        "jam_verifikasi_uf": None,
        "tanggal_verifikasi_uu": None,
        "jam_verifikasi_uu": None,
        "tanggal_penjadwalan_inaktif": date(2026, 8, 31),
        "jam_penjadwalan_inaktif": time(9, 0),
        "tanggal_jadwal_penjemputan": date(2026, 9, 1),
        "jam_jadwal_penjemputan": time(8, 0),
        "tanggal_penjemputan_dokumen": date(2026, 9, 1),
        "jam_penjemputan_dokumen": time(8, 30),
        "tanggal_registrasi_2": None,
        "jam_registrasi_2": None,
        "tanggal_verifikasi_arsip_2": None,
        "jam_verifikasi_arsip_2": None,
        "tanggal_penolakan_jadwal_penjemputan": None,
        "jam_penolakan_jadwal_penjemputan": None,
        "tanggal_gagal_penjemputan": None,
        "jam_gagal_penjemputan": None,
        "tanggal_penjadwalan_inaktif_2": date(2026, 8, 31),
        "jam_penjadwalan_inaktif_2": time(8, 0),
    }
    row.update(overrides)
    return row


def assert_manual_vendor_yes(row, expected_rule):
    result = SLA2Calculator.evaluate_vendor(row, dict(CTX))
    assert result["result"] == "Yes"
    assert result["manual_result"] == "Yes"
    assert expected_rule in [x.strip() for x in str(result["manual_rule"]).split("|") if x.strip()]
    return result


# ---------------------------------------------------------------------------
# SLA 2A — all approved patterns / rules
# ---------------------------------------------------------------------------

SLA2A_PATTERNS = [
    (
        "SLA2A-01 Ready To Pick Up + '-' + Runner + Fisik + Inaktif",
        dict(status_registrasi="Ready To Pick Up", status_inisiasi="-", posisi_data="Runner", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-01-READY-TO-PICKUP-RUNNER-INAKTIF",
    ),
    (
        "SLA2A-01B Ready To Pick Up + Diverifikasi Unit Umum + Runner + Fisik + Inaktif",
        dict(status_registrasi="Ready To Pick Up", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Runner", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-01B-READY-TO-PICKUP-RUNNER-DIVERIFIKASI-UMUM-INAKTIF",
    ),
    (
        "SLA2A-02 Scheduled + '-' + MSB / Unit Fungsi + Fisik + Inaktif",
        dict(status_registrasi="Scheduled", status_inisiasi="-", posisi_data="MSB / Unit Fungsi", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-02-SCHEDULED-MSB-UNIT-FUNGSI-INAKTIF",
    ),
    (
        "SLA2A-03 Diarsipkan + '-' + Record Center + Fisik + Inaktif",
        dict(status_registrasi="Diarsipkan", status_inisiasi="-", posisi_data="Record Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-03-DIARSIPKAN-RECORD-CENTER-FISIK-INAKTIF",
    ),
    (
        "SLA2A-04 Pickup Failed + '-' + posisi kosong + Fisik + Inaktif",
        dict(status_registrasi="Pickup Failed", status_inisiasi="-", posisi_data="", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-04-PICKUP-FAILED-EMPTY-POSITION-INAKTIF",
    ),
    (
        "SLA2A-05 On Location + '-' + Runner + Fisik + Inaktif",
        dict(status_registrasi="On Location", status_inisiasi="-", posisi_data="Runner", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-05-ON-LOCATION-RUNNER-INAKTIF",
    ),
    (
        "SLA2A-06 Registrasi Masuk + '-' + Command Center + Fisik + Inaktif",
        dict(status_registrasi="Registrasi Masuk", status_inisiasi="-", posisi_data="Command Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-06-REGISTRASI-MASUK-COMMAND-CENTER-INAKTIF",
    ),
    (
        "SLA2A-07 Ditolak Command Center prefix + '-' + posisi kosong + Fisik + Inaktif",
        dict(status_registrasi="Ditolak Command Center (Mohon perbaiki data)", status_inisiasi="-", posisi_data="", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-07-DITOLAK-COMMAND-CENTER-INAKTIF",
    ),
    (
        "SLA2A-08 Registrasi Masuk Lanjutan + Diverifikasi Unit Umum + Command Center + Fisik + Inaktif",
        dict(status_registrasi="Registrasi Masuk Lanjutan", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Command Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-08-REGISTRASI-MASUK-LANJUTAN-COMMAND-CENTER-INAKTIF",
    ),
    (
        "SLA2A-09 Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif",
        dict(status_registrasi="Diarsipkan", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Record Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2A-09-DIARSIPKAN-DIVERIFIKASI-UMUM-RECORD-CENTER-INAKTIF",
    ),
    (
        "SLA2A-10 Diarsipkan + '-' + Record Center + Digital + Inaktif + named workflow fields",
        dict(
            status_registrasi="Diarsipkan", status_inisiasi="-", posisi_data="Record Center",
            format_arsip="Digital", document_type="Inaktif",
            tanggal_penjadwalan_inaktif=date(2026, 8, 3),
            jam_penjadwalan_inaktif=time(9, 15),
            tanggal_jadwal_penjemputan=date(2026, 8, 6),
            jam_jadwal_penjemputan=time(8, 0),
        ),
        "MC-SLA2A-10-DIARSIPKAN-RECORD-CENTER-DIGITAL-INAKTIF",
    ),
]


@pytest.mark.parametrize("name,overrides,rule", SLA2A_PATTERNS, ids=[p[0] for p in SLA2A_PATTERNS])
def test_sla2a_each_approved_manual_pattern(name, overrides, rule):
    # Disable the SLA 2B end pair so the SLA 2B manual rules cannot intercept.
    row = base(**overrides, tanggal_penjadwalan_inaktif_2=None, jam_penjadwalan_inaktif_2=None)
    # Direct branch test guarantees that every SLA 2A rule is individually matched.
    branch = apply_sla2a_manual_check(row, dict(CTX))
    assert branch["result"] == "Yes"
    assert branch["rule_code"] == rule
    result = assert_manual_vendor_yes(row, rule)
    assert result["sla_2a_result"] in {"No", "N/A"}


# ---------------------------------------------------------------------------
# SLA 2B — 9 existing approved patterns + VIP approved pattern
# ---------------------------------------------------------------------------

SLA2B_PATTERNS = [
    (
        "SLA2B-01 Pickup Failed + Fisik + Inaktif",
        dict(status_registrasi="Pickup Failed", status_inisiasi="-", posisi_data="", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-01-PICKUP-FAILED",
    ),
    (
        "SLA2B-02 Diarsipkan + '-' + Record Center + Fisik + Inaktif",
        dict(status_registrasi="Diarsipkan", status_inisiasi="-", posisi_data="Record Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-02-DIARSIPKAN-RECORD-CENTER-INAKTIF",
    ),
    (
        "SLA2B-03 Ready To Pick Up + '-' + Runner + Fisik + Inaktif",
        dict(status_registrasi="Ready To Pick Up", status_inisiasi="-", posisi_data="Runner", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-03-READY-TO-PICKUP-RUNNER-INAKTIF",
    ),
    (
        "SLA2B-04 Scheduled + Diverifikasi Unit Umum + MSB / Unit Fungsi + Fisik + Aktif",
        dict(status_registrasi="Scheduled", status_inisiasi="Diverifikasi Unit Umum", posisi_data="MSB / Unit Fungsi", format_arsip="Fisik", document_type="Aktif"),
        "MC-SLA2B-04-SCHEDULED-MSB-UNIT-FUNGSI-AKTIF",
    ),
    (
        "SLA2B-05 Scheduled + '-' + MSB / Unit Fungsi + Fisik + Inaktif",
        dict(status_registrasi="Scheduled", status_inisiasi="-", posisi_data="MSB / Unit Fungsi", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-05-SCHEDULED-MSB-UNIT-FUNGSI-INAKTIF",
    ),
    (
        "SLA2B-06 On Location + Runner + Fisik + Inaktif",
        dict(status_registrasi="On Location", status_inisiasi="-", posisi_data="Runner", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-06-ON-LOCATION-RUNNER-INAKTIF",
    ),
    (
        "SLA2B-07 Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif",
        dict(status_registrasi="Diarsipkan", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Record Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-07-DIARSIPKAN-RECORD-CENTER-DIVERIFIKASI-UMUM",
    ),
    (
        "SLA2B-08 Ready To Pick Up + Diverifikasi Unit Umum + Runner + Fisik + Aktif",
        dict(status_registrasi="Ready To Pick Up", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Runner", format_arsip="Fisik", document_type="Aktif"),
        "MC-SLA2B-08-READY-TO-PICKUP-RUNNER-AKTIF",
    ),
    (
        "SLA2B-09 On Location + Diverifikasi Unit Umum + Runner + Fisik + Aktif",
        dict(status_registrasi="On Location", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Runner", format_arsip="Fisik", document_type="Aktif"),
        "MC-SLA2B-09-ON-LOCATION-RUNNER-AKTIF",
    ),
    (
        "SLA2B-10 VIP + Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif",
        dict(sumber="VIP", status_registrasi="Diarsipkan", status_inisiasi="Diverifikasi Unit Umum", posisi_data="Record Center", format_arsip="Fisik", document_type="Inaktif"),
        "MC-SLA2B-10-VIP-DIARSIPKAN-RECORD-CENTER-INAKTIF",
    ),
]


@pytest.mark.parametrize("name,overrides,rule", SLA2B_PATTERNS, ids=[p[0] for p in SLA2B_PATTERNS])
def test_sla2b_each_approved_manual_pattern(name, overrides, rule):
    row = base(**overrides)
    branch = apply_sla2b_manual_check(row, dict(CTX))
    assert branch["result"] == "Yes"
    assert branch["rule_code"] == rule
    result = assert_manual_vendor_yes(row, rule)
    assert result["sla_2b_result"] == "N/A"


# ---------------------------------------------------------------------------
# Formula/flow guards
# ---------------------------------------------------------------------------


def test_sla2a_formula_yes_is_kept_and_manual_is_not_used():
    row = base(
        tanggal_registrasi=date(2026, 8, 24),
        tanggal_penjadwalan_inaktif=date(2026, 8, 26),
    )
    result = SLA2Calculator.evaluate_vendor(row, dict(CTX))
    assert result["sla_2a_result"] == "Yes"
    assert result["result"] == "Yes"
    assert result["manual_result"] == "N/A"


def test_sla2a_formula_requires_registration_time_and_inactive_schedule_pair():
    row = base(jam_registrasi=None)
    result = SLA2Calculator.evaluate_sla_2a(row, dict(CTX))
    assert result["result"] == "N/A"

    row2 = base(jam_penjadwalan_inaktif=None)
    result2 = SLA2Calculator.evaluate_sla_2a(row2, dict(CTX))
    assert result2["result"] == "N/A"


def test_sla2_period_gate_blocks_manual_override_at_august_last_working_day_2():
    row = base(
        status_registrasi="Ready To Pick Up",
        posisi_data="Runner",
        tanggal_registrasi=date(2026, 8, 28),
    )
    result = SLA2Calculator.evaluate_vendor(row, dict(CTX))
    assert result["sla_2a_result"] == "N/A"
    assert result["sla_2b_result"] == "N/A"
    assert result["manual_result"] == "N/A"
    assert result["result"] == "N/A"


def test_sla2b_out_of_period_july_29_stays_blocked_for_manual_override():
    row = base(
        status_registrasi="On Location",
        status_inisiasi="Diverifikasi Unit Umum",
        posisi_data="Runner",
        format_arsip="Fisik",
        document_type="Aktif",
        tanggal_registrasi=date(2026, 7, 29),
        tanggal_penjadwalan_inaktif_2=date(2026, 7, 30),
        jam_penjadwalan_inaktif_2=time(8, 0),
    )
    branch = apply_sla2b_manual_check(row, dict(CTX))
    assert branch["result"] == "N/A"
    result = SLA2Calculator.evaluate_vendor(row, dict(CTX))
    assert result["sla_2b_result"] == "N/A"
    assert result["result"] != "Yes"


def test_sla2a_digital_manual_requires_named_inactive_schedule_and_pickup_schedule():
    common = dict(
        status_registrasi="Diarsipkan", status_inisiasi="-", posisi_data="Record Center",
        format_arsip="Digital", document_type="Inaktif",
        tanggal_registrasi=date(2026, 8, 10),
    )
    missing_pickup = base(
        **common,
        tanggal_penjadwalan_inaktif=date(2026, 8, 3),
        jam_penjadwalan_inaktif=time(9, 15),
        tanggal_jadwal_penjemputan=None,
        jam_jadwal_penjemputan=None,
        tanggal_penjadwalan_inaktif_2=None,
        jam_penjadwalan_inaktif_2=None,
    )
    assert apply_sla2a_manual_check(missing_pickup, dict(CTX))["result"] == "N/A"


def test_sla2b_z_path_has_priority_and_cutoff_is_respected():
    row = base(
        tanggal_registrasi=date(2026, 8, 20),
        tanggal_registrasi_2=date(2026, 8, 25),
        jam_registrasi_2=time(8, 0),
        tanggal_penjadwalan_inaktif_2=date(2026, 8, 27),
        jam_penjadwalan_inaktif_2=time(10, 0),
        # Other paths are deliberately populated too; Z must win first.
        tanggal_gagal_penjemputan=date(2026, 8, 25),
        jam_gagal_penjemputan=time(8, 0),
        tanggal_penolakan_jadwal_penjemputan=date(2026, 8, 25),
        jam_penolakan_jadwal_penjemputan=time(8, 0),
    )
    result = SLA2Calculator.evaluate_sla_2b(row, dict(CTX))
    assert result["result"] == "Yes"
    assert result["working_days"] == 2

    late_cutoff = dict(row, jam_penjadwalan_inaktif_2=time(10, 0, 1))
    result_late = SLA2Calculator.evaluate_sla_2b(late_cutoff, dict(CTX))
    assert result_late["result"] == "No"


def test_sla2_final_is_yes_when_either_branch_is_yes():
    row = base(
        status_registrasi="Ready To Pick Up",
        status_inisiasi="-",
        posisi_data="Runner",
        tanggal_registrasi=date(2026, 8, 10),
        tanggal_penjadwalan_inaktif=date(2026, 8, 11),
        tanggal_penjadwalan_inaktif_2=date(2026, 8, 26),
        jam_penjadwalan_inaktif_2=time(8, 0),
    )
    result = SLA2Calculator.evaluate_vendor(row, dict(CTX))
    assert result["sla_2a_result"] == "Yes"
    assert result["result"] == "Yes"
    assert result["manual_result"] == "N/A"


def test_pending_ditolak_command_center_is_not_a_sla2b_manual_rule():
    # This is the mentor-pending special case. SLA 2A may be handled by its own
    # approved prefix rule, but there is intentionally no SLA 2B manual rule.
    row = base(
        status_registrasi="Ditolak Command Center (Mohon perbaiki data)",
        tanggal_registrasi=date(2026, 8, 20),
        tanggal_penjadwalan_inaktif_2=None,
        jam_penjadwalan_inaktif_2=None,
    )
    branch_b = apply_sla2b_manual_check(row, dict(CTX))
    assert branch_b["result"] == "N/A"
    assert branch_b["rule_code"] is None
