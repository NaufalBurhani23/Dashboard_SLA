from datetime import date, time

from app.sla.sla1.calculator import SLA1Calculator
from app.services.excel_parser import build_period_context


CTX = {
    # Agustus 2026: H-1 = Hari Kerja Terakhir Hari ke-1,
    # H-2 = Hari Kerja Terakhir Hari ke-2, H-3 = Hari Kerja Terakhir Hari ke-3.
    "current_last_working_day_1": date(2026, 8, 31),
    "current_last_working_day_2": date(2026, 8, 28),
    "current_last_working_day_3": date(2026, 8, 27),
    # Juli 2026: urutan H-1/H-2/H-3 menggunakan bulan sebelumnya.
    "previous_last_working_day_1": date(2026, 7, 31),
    "previous_last_working_day_2": date(2026, 7, 30),
    "previous_last_working_day_3": date(2026, 7, 29),
    "cutoff": time(10, 0),
    "holidays": [],
    "period_label": "2026-08",
}


def test_period_context_uses_ordinal_last_working_day_terminology():
    context = build_period_context([date(2026, 8, 3), date(2026, 8, 31)], [])

    assert context["current_last_working_day_1"] == date(2026, 8, 31)
    assert context["current_last_working_day_2"] == date(2026, 8, 28)
    assert context["current_last_working_day_3"] == date(2026, 8, 27)
    assert context["previous_last_working_day_1"] == date(2026, 7, 31)
    assert context["previous_last_working_day_2"] == date(2026, 7, 30)
    assert context["previous_last_working_day_3"] == date(2026, 7, 29)


def base():
    return {
        "format_arsip": "Digital",
        "document_type": "Aktif",
        "tanggal_registrasi": date(2026, 8, 3),
        "jam_registrasi": time(8, 0),
        "tanggal_verifikasi_uf": None,
        "jam_verifikasi_uf": None,
        "tanggal_verifikasi_uu": None,
        "jam_verifikasi_uu": None,
        "tanggal_verifikasi_arsip": date(2026, 8, 3),
        "jam_verifikasi_arsip": time(9, 0),
        "tanggal_registrasi_2": None,
        "jam_registrasi_2": None,
        "tanggal_verifikasi_arsip_2": None,
        "jam_verifikasi_arsip_2": None,
        "nama_dokumen": "Dokumen",
        "sumber": "unknown",
        "status_registrasi": "unknown",
        "status_inisiasi": "unknown",
        "posisi_data": "unknown",
        "tanggal_penjadwalan_inaktif": None,
        "jam_penjadwalan_inaktif": None,
        "tanggal_jadwal_penjemputan": None,
        "jam_jadwal_penjemputan": None,
        "tanggal_penjemputan_dokumen": None,
        "jam_penjemputan_dokumen": None,
        "tanggal_runner_sampai_record_center": None,
        "jam_runner_sampai_record_center": None,
        "tanggal_registrasi_arsip_generate_barcode": None,
        "jam_registrasi_arsip_generate_barcode": None,
    }


def test_sla1a_yes_short_circuits_and_1b_is_na():
    r = SLA1Calculator.evaluate_vendor(base(), CTX)
    assert r["result"] == "Yes"
    assert r["sla_1a_result"] == "Yes"
    assert r["sla_1b_result"] == "N/A"
    assert r["flow_stage"] == "SLA_1A_YES"


def test_sla1a_no_continues_to_1b():
    row = base()
    row.update(
        {
            "tanggal_verifikasi_arsip": date(2026, 8, 10),
            "jam_verifikasi_arsip": time(17, 0),
            "tanggal_registrasi_2": date(2026, 8, 3),
            "jam_registrasi_2": time(8, 0),
            "tanggal_verifikasi_arsip_2": date(2026, 8, 3),
            "jam_verifikasi_arsip_2": time(9, 0),
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["sla_1a_result"] == "No"
    assert r["sla_1b_result"] == "Yes"
    assert r["result"] == "Yes"
    assert r["flow_stage"] == "SLA_1B_YES"


def test_hari_kerja_terakhir_ke_2_is_not_resurrected_by_manual_rule():
    row = base()
    row.update(
        {
            "tanggal_registrasi": date(2026, 8, 28),
            "sumber": "ELARCH",
            "status_registrasi": "Verifikasi Command Center",
            "status_inisiasi": "-",
            "posisi_data": "",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["sla_1a_result"] == "N/A"
    assert r["sla_1b_result"] == "N/A"
    assert r["result"] == "N/A"
    assert r["flow_stage"] == "FINAL_NA"


def test_hari_kerja_terakhir_ke_1_is_not_resurrected_by_manual_rule():
    row = base()
    row.update(
        {
            "tanggal_registrasi": date(2026, 8, 31),
            "sumber": "ELARCH",
            "status_registrasi": "Verifikasi Command Center",
            "status_inisiasi": "-",
            "posisi_data": "",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["result"] == "N/A"
    assert r["flow_stage"] == "FINAL_NA"


def test_record_center_inactive_workflow_stays_na():
    row = base()
    row.update(
        {
            "tanggal_registrasi": date(2026, 7, 29),
            "sumber": "ELARCH",
            "status_registrasi": "Diarsipkan",
            "status_inisiasi": "-",
            "posisi_data": "Record Center",
            "format_arsip": "Digital",
            "document_type": "Inaktif",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
            "tanggal_penjadwalan_inaktif": date(2026, 8, 3),
            "jam_penjadwalan_inaktif": time(9, 15),
            "tanggal_jadwal_penjemputan": date(2026, 8, 6),
            "jam_jadwal_penjemputan": time(8, 0),
            "tanggal_penjemputan_dokumen": date(2026, 8, 6),
            "jam_penjemputan_dokumen": time(10, 58),
            "tanggal_runner_sampai_record_center": date(2026, 8, 6),
            "jam_runner_sampai_record_center": time(14, 39),
            "tanggal_registrasi_arsip_generate_barcode": date(2026, 8, 12),
            "jam_registrasi_arsip_generate_barcode": time(14, 14),
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["result"] == "N/A"
    assert r["flow_stage"] == "FINAL_NA"


def test_vip_ditolak_command_center_prefix_is_manual_yes():
    row = base()
    row.update(
        {
            "sumber": "VIP",
            "status_registrasi": "Ditolak Command Center (Sesuai request UF bahwa arsip fisiknya masih dalam proses pencarian.)",
            "status_inisiasi": "Diverifikasi Unit Umum",
            "posisi_data": "",
            "format_arsip": "Fisik",
            "document_type": "Aktif",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["result"] == "Yes"
    assert r["sla_1a_result"] == "N/A"
    assert r["sla_1b_result"] == "N/A"
    assert r["decision_source"] == "MANUAL VENDOR RULE"
    assert r["manual_rule"] == "MC-SLA1-VIP-DITOLAK-CC"


def test_elarch_ditolak_command_center_prefix_supports_allowed_formats():
    for fmt, doc in (("Fisik", "Aktif"), ("Digital", "Aktif"), ("Digital", "Inaktif")):
        row = base()
        row.update(
            {
                "sumber": "ELARCH",
                "status_registrasi": "Ditolak Command Center (Mohon perbaiki data registrasi.)",
                "status_inisiasi": "-",
                "posisi_data": "",
                "format_arsip": fmt,
                "document_type": doc,
                "tanggal_verifikasi_arsip": None,
                "jam_verifikasi_arsip": None,
            }
        )
        r = SLA1Calculator.evaluate_vendor(row, CTX)
        assert r["result"] == "Yes"
        assert r["manual_rule"] == "MC-SLA1-ELARCH-DITOLAK-CC"


def test_elarch_ditolak_fisik_inaktif_does_not_bypass_format_gate():
    row = base()
    row.update(
        {
            "sumber": "ELARCH",
            "status_registrasi": "Ditolak Command Center (x)",
            "status_inisiasi": "-",
            "posisi_data": "",
            "format_arsip": "Fisik",
            "document_type": "Inaktif",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["result"] == "N/A"


def test_elarch_runner_is_manual_yes_when_formula_is_not_yes():
    row = base()
    row.update(
        {
            "sumber": "ELARCH",
            "status_registrasi": "Diarsipkan",
            "status_inisiasi": "-",
            "posisi_data": "Runner",
            "format_arsip": "Digital",
            "document_type": "Inaktif",
            "tanggal_verifikasi_arsip": date(2026, 8, 7),
            "jam_verifikasi_arsip": time(9, 15, 30),
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["sla_1a_result"] == "No"
    assert r["sla_1b_result"] == "N/A"
    assert r["result"] == "Yes"
    assert r["manual_rule"] == "MC-SLA1-ELARCH-DIARSIPKAN-POSISI"


def test_both_na_without_manual_match_stays_na():
    row = base()
    row.update(
        {
            "format_arsip": "Fisik",
            "document_type": "Inaktif",
            "tanggal_verifikasi_arsip": None,
            "jam_verifikasi_arsip": None,
            "tanggal_registrasi_2": None,
            "jam_registrasi_2": None,
            "tanggal_verifikasi_arsip_2": None,
            "jam_verifikasi_arsip_2": None,
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["result"] == "N/A"
    assert r["flow_stage"] == "FINAL_NA"


def test_no_from_formula_has_final_no_when_manual_does_not_match():
    row = base()
    row.update(
        {
            "tanggal_verifikasi_arsip": date(2026, 8, 10),
            "jam_verifikasi_arsip": time(17, 0),
            "tanggal_registrasi_2": None,
            "jam_registrasi_2": None,
            "tanggal_verifikasi_arsip_2": None,
            "jam_verifikasi_arsip_2": None,
            "sumber": "lain",
            "status_registrasi": "lain",
        }
    )
    r = SLA1Calculator.evaluate_vendor(row, CTX)
    assert r["sla_1a_result"] == "No"
    assert r["sla_1b_result"] == "N/A"
    assert r["result"] == "No"
    assert r["flow_stage"] == "FINAL_NO"
