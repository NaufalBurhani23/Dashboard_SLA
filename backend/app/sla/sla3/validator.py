"""Validator for SLA 3 records."""
from typing import Any, Dict


def validate_sla3_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Validate raw row data for SLA 3 prerequisites."""
    errors = []
    
    # Contoh validasi dasar format arsip
    format_arsip = str(row.get("format_arsip", "")).strip().lower()
    if format_arsip and format_arsip not in {"fisik", "digital"}:
        errors.append("Format arsip tidak valid untuk SLA 3 (harus fisik/digital).")

    # Pastikan tanggal registrasi ada
    if not row.get("tanggal_registrasi"):
        errors.append("Tanggal registrasi kosong.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }