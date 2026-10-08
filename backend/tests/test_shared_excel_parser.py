from pathlib import Path
from app.services.excel_parser import parse_registrasi_sheet


def test_vendor_header_mapping_uses_named_headers():
    workbook = Path("/mnt/data/PLN_Archive_Service_Hub_SLA_Calculations_August_2026_vFinal_080920261.xlsx")
    if not workbook.exists():
        return
    records, context = parse_registrasi_sheet(workbook.read_bytes(), holidays=[])
    assert records
    assert records[0]["unit"] != "Tanpa Unit"
    assert "tanggal_jadwal_penjemputan" in records[0]
    assert "tanggal_gagal_penjemputan" in records[0]
    assert "tanggal_penjadwalan_inaktif_2" in records[0]
    assert "tanggal_runner_record_center" in records[0]
    assert "tanggal_registrasi_arsip_generate_barcode" in records[0]
    assert context["period_label"] == "2026-08"
