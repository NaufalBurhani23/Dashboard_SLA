from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.sla.sla4.parser import parse_sla4_workbook


def test_parser_uses_names_not_column_order_and_handles_duplicate_registration_header():
    wb = Workbook()
    ws = wb.active
    ws.title = "Raw"
    headers = [
        "Status Registrasi",
        "Unit Umum",
        "Tanggal Penjemputan Dokumen",
        "Jam Penjemputan Dokumen",
        "No. Registrasi",
        "Tanggal Registrasi",
        "Tipe Arsip",
        "Sumber",
        "Tanggal Jadwal Penjemputan",
        "Jam Jadwal Penjemputan",
        "Format Dokumen",
        "Status Inisiasi",
        "Posisi Data",
        "Jenis Dokumen",
        "Tanggal Registrasi",
        "Jam Registrasi",
        "Tanggal Verifikasi Arsip",
        "Jam Verifikasi Arsip",
        "Tanggal Runner sampai di Record Center",
        "Jam Runner sampai di Record Center",
        "Tanggal Penolakan Jadwal Penjemputan",
        "Jam Penolakan Jadwal Penjemputan",
        "Tanggal Gagal Penjemputan",
        "Jam Gagal Penjemputan",
        "Tanggal Penjadwalan Arsip Inaktif",
        "Jam Penjadwalan Arsip Inaktif",
        "Tanggal Penjadwalan Arsip Inaktif 2",
        "Jam Penjadwalan Arsip Inaktif 2",
    ]
    ws.append(headers)
    row = [None] * len(headers)
    values = {
        "Status Registrasi": "Diarsipkan",
        "Unit Umum": "UID Banten",
        "No. Registrasi": "REG-001",
        "Tipe Arsip": "Fisik",
        "Sumber": "ELARCH",
        "Status Inisiasi": "-",
        "Posisi Data": "Record Center",
        "Jenis Dokumen": "Inaktif",
        "Tanggal Registrasi#1": datetime(2026, 8, 1),
        "Tanggal Registrasi#2": datetime(2026, 8, 10),
        "Jam Registrasi": datetime(1900, 1, 1, 8, 30),
        "Tanggal Jadwal Penjemputan": datetime(2026, 8, 13),
        "Jam Jadwal Penjemputan": datetime(1900, 1, 1, 9, 0),
        "Tanggal Penjemputan Dokumen": datetime(2026, 8, 14),
        "Jam Penjemputan Dokumen": datetime(1900, 1, 1, 10, 0),
        "Tanggal Verifikasi Arsip": datetime(2026, 8, 13),
        "Jam Verifikasi Arsip": datetime(1900, 1, 1, 8, 0),
        "Tanggal Runner sampai di Record Center": datetime(2026, 8, 14),
        "Jam Runner sampai di Record Center": datetime(1900, 1, 1, 11, 0),
        "Tanggal Penjadwalan Arsip Inaktif": datetime(2026, 8, 10),
        "Jam Penjadwalan Arsip Inaktif": datetime(1900, 1, 1, 9, 0),
    }
    seen_reg = 0
    for i, h in enumerate(headers):
        if h == "Tanggal Registrasi":
            seen_reg += 1
            row[i] = values[f"Tanggal Registrasi#{seen_reg}"]
        elif h in values:
            row[i] = values[h]
    ws.append(row)

    out = BytesIO()
    wb.save(out)
    records, period, info = parse_sla4_workbook(out.getvalue())
    assert period == "2026-08"
    assert records[0]["unit"] == "UID Banten"
    assert records[0]["tanggal_registrasi"].day == 10
    assert records[0]["tanggal_jadwal_penjemputan"].day == 13
    assert records[0]["tanggal_penjemputan_dokumen"].day == 14
    assert "tanggal_runner_record_center" in records[0]
    assert info["header_row"] == 1
