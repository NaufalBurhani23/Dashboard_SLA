"""Validated manual override patterns for SLA 3A and SLA 3B.

Business rules are evaluated only after the corresponding Excel formula has
run and returned something other than `Yes`. Manual override never bypasses
the Period Gate.

All conditions use RAW DATA HEADER NAMES represented by the parser, never
Excel column letters.

Patterns implemented based on validated pending/exception records:
1. Registrasi Masuk (Command Center)
2. Registrasi Masuk Lanjutan (Command Center)
3. Pickup Failed (tanpa posisi)
4. Pickup Failed + Diverifikasi Unit Umum (tanpa posisi)
5. Ditolak Command Center (kembali ke User/revisi)
"""
from datetime import date, datetime
from typing import Any, Dict, Optional


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _empty(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _as_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def _canon_text(value: Any) -> str:
    value = _norm(value)
    return value.replace(" / ", "/")


def _is_pos(value: Any, *names: str) -> bool:
    value = _canon_text(value)
    return any(value == _canon_text(name) for name in names)


def _is_init(value: Any, *names: str) -> bool:
    value = _canon_text(value)
    return any(value == _canon_text(name) for name in names)


def _status_starts_with(value: Any, prefix: str) -> bool:
    value_n = _norm(value)
    prefix_n = _norm(prefix)
    return value_n == prefix_n or value_n.startswith(prefix_n + " ")


def _has_pair(row: Dict[str, Any], date_key: str, time_key: str) -> bool:
    return not _empty(row.get(date_key)) and not _empty(row.get(time_key))


def _period_gate(row: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Apply the exact Period Gate for SLA 3 from the vendor formulas."""
    p = _as_date(context.get("registration_date")) or _as_date(row.get("tanggal_registrasi"))
    if p is None:
        return False

    h5, h6, h8, h9 = context["h5"], context["h6"], context["h8"], context["h9"]
    # SLA 3 (Sama dengan SLA 2A): OR(P>=H9, P<=H8) AND P<H6 AND P<>H5
    return (p >= h9 or p <= h8) and (p < h6 and p != h5)


def _blocked_period_result() -> Dict[str, Any]:
    return {
        "result": "N/A",
        "rule_code": None,
        "reason": "Manual override SLA 3 diblokir karena Tanggal Registrasi berada di luar Period Gate.",
    }


def apply_sla3_manual_check(row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply only the approved SLA 3 manual patterns."""
    if not _period_gate(row, context):
        return _blocked_period_result()

    source = _canon_text(row.get("sumber"))
    status = _canon_text(row.get("status_registrasi"))
    init = _canon_text(row.get("status_inisiasi"))
    position = _canon_text(row.get("posisi_data"))
    fmt = _canon_text(row.get("format_arsip"))

    # Syarat mutlak format arsip untuk SLA 3
    if fmt != "fisik":
        return {
            "result": "N/A",
            "rule_code": None,
            "reason": "SLA 3 Manual: Format Arsip bukan fisik.",
        }

    # M3-01 — ACC: ELARCH + Registrasi Masuk + '-' + Command Center + Fisik
    if (
        source == "elarch"
        and status == "registrasi masuk"
        and _is_init(init, "-")
        and _is_pos(position, "command center")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA3-01-REGISTRASI-MASUK-COMMAND-CENTER",
            "reason": "Pola SLA 3 ACC: ELARCH + Registrasi Masuk + Status Inisiasi '-' + Posisi Command Center + Fisik.",
        }

    # M3-02 — ACC: ELARCH + Registrasi Masuk Lanjutan + Diverifikasi Unit Umum + Command Center + Fisik
    if (
        source == "elarch"
        and status == "registrasi masuk lanjutan"
        and _is_init(init, "diverifikasi unit umum")
        and _is_pos(position, "command center")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA3-02-REGISTRASI-MASUK-LANJUTAN-DIVERIFIKASI-COMMAND-CENTER",
            "reason": "Pola SLA 3 ACC: ELARCH + Registrasi Masuk Lanjutan + Status Inisiasi Diverifikasi Unit Umum + Posisi Command Center + Fisik.",
        }

    # M3-03 — ACC: ELARCH + Pickup Failed + '-' + Posisi Kosong + Fisik
    if (
        source == "elarch"
        and status == "pickup failed"
        and _is_init(init, "-")
        and _is_pos(position, "")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA3-03-PICKUP-FAILED-EMPTY-POSITION",
            "reason": "Pola SLA 3 ACC: ELARCH + Pickup Failed + Status Inisiasi '-' + Posisi Data Kosong + Fisik.",
        }

    # M3-04 — ACC: ELARCH + Pickup Failed + Diverifikasi Unit Umum + Posisi Kosong + Fisik
    if (
        source == "elarch"
        and status == "pickup failed"
        and _is_init(init, "diverifikasi unit umum")
        and _is_pos(position, "")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA3-04-PICKUP-FAILED-DIVERIFIKASI-EMPTY-POSITION",
            "reason": "Pola SLA 3 ACC: ELARCH + Pickup Failed + Status Inisiasi Diverifikasi Unit Umum + Posisi Data Kosong + Fisik.",
        }

    # M3-05 — ACC: ELARCH + Prefix "Ditolak Command Center" + '-' + Posisi Kosong + Fisik
    if (
        source == "elarch"
        and _status_starts_with(status, "ditolak command center")
        and _is_init(init, "-")
        and _is_pos(position, "")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA3-05-DITOLAK-COMMAND-CENTER",
            "reason": "Pola SLA 3 ACC: ELARCH + Status Registrasi prefix 'Ditolak Command Center' + Status Inisiasi '-' + Posisi Data kosong + Fisik.",
        }

    return {
        "result": "N/A",
        "rule_code": None,
        "reason": "Tidak ditemukan pola manual SLA 3 yang telah di-ACC.",
    }