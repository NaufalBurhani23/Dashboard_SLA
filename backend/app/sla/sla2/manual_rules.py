"""Validated manual override patterns for SLA 2A and SLA 2B.

Business rules are evaluated only after the corresponding Excel formula has
run and returned something other than ``Yes``. Manual override never bypasses
the branch-specific Period Gate.

All conditions use RAW DATA HEADER NAMES represented by the parser, never
Excel column letters such as X/Y/AW/AY.

Pending mentor case:
- SLA 2B records whose registration date is outside the SLA 2B Period Gate
  remain blocked for now (mentor validation pending).
- The special 5040/5041-style SLA 2B exception is intentionally not coded as
  a new manual pattern.
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


def _period_gate(row: Dict[str, Any], context: Dict[str, Any], branch: str) -> bool:
    """Apply the exact branch-specific Period Gate from the vendor formulas."""
    p = _as_date(context.get("registration_date")) or _as_date(row.get("tanggal_registrasi"))
    if p is None:
        return False

    h5, h6, h8, h9 = context["h5"], context["h6"], context["h8"], context["h9"]
    if branch == "2B":
        # OR(P>=H9, P=H8) AND P<H6 AND P<>H5
        return (p >= h9 or p == h8) and (p < h6 and p != h5)

    # SLA 2A: OR(P>=H9, P<=H8) AND P<H6 AND P<>H5
    return (p >= h9 or p <= h8) and (p < h6 and p != h5)


def _blocked_period_result(branch: str) -> Dict[str, Any]:
    return {
        "result": "N/A",
        "rule_code": None,
        "reason": f"Manual override {branch} diblokir karena Tanggal Registrasi berada di luar Period Gate {branch}.",
    }


def apply_sla2a_manual_check(row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply only the approved SLA 2A manual patterns."""
    if not _period_gate(row, context, "2A"):
        return _blocked_period_result("SLA 2A")

    source = _canon_text(row.get("sumber"))
    status = _canon_text(row.get("status_registrasi"))
    init = _canon_text(row.get("status_inisiasi"))
    position = _canon_text(row.get("posisi_data"))
    fmt = _canon_text(row.get("format_arsip"))
    doc = _canon_text(row.get("document_type"))

    # A1 — ACC: ELARCH + Ready To Pick Up + '-' + Runner + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "ready to pick up"
        and _is_init(init, "-")
        and _is_pos(position, "runner")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-01-READY-TO-PICKUP-RUNNER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Ready To Pick Up + Status Inisiasi '-' + Runner + Fisik + Inaktif.",
        }

    # A1B — separate rule for the one validated record whose Status Inisiasi
    # is Diverifikasi Unit Umum. The main A1 rule remains '-' only.
    if (
        source == "elarch"
        and status == "ready to pick up"
        and _is_init(init, "diverifikasi unit umum")
        and _is_pos(position, "runner")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-01B-READY-TO-PICKUP-RUNNER-DIVERIFIKASI-UMUM-INAKTIF",
            "reason": "Pola SLA 2A tambahan terverifikasi: ELARCH + Ready To Pick Up + Status Inisiasi Diverifikasi Unit Umum + Runner + Fisik + Inaktif.",
        }

    # A2 — ACC: ELARCH + Scheduled + '-' + MSB / Unit Fungsi + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "scheduled"
        and _is_init(init, "-")
        and _is_pos(position, "msb / unit fungsi", "msb/unit fungsi")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-02-SCHEDULED-MSB-UNIT-FUNGSI-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Scheduled + Status Inisiasi '-' + MSB / Unit Fungsi + Fisik + Inaktif.",
        }

    # A3 — ACC: ELARCH + Diarsipkan + '-' + Record Center + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "diarsipkan"
        and _is_init(init, "-")
        and _is_pos(position, "record center")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-03-DIARSIPKAN-RECORD-CENTER-FISIK-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Diarsipkan + Status Inisiasi '-' + Record Center + Fisik + Inaktif.",
        }

    # A4 — ACC: ELARCH + Pickup Failed + '-' + posisi kosong + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "pickup failed"
        and _is_init(init, "-")
        and _is_pos(position, "")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-04-PICKUP-FAILED-EMPTY-POSITION-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Pickup Failed + Status Inisiasi '-' + Posisi Data kosong + Fisik + Inaktif.",
        }

    # A5 — ACC: ELARCH + On Location + '-' + Runner + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "on location"
        and _is_init(init, "-")
        and _is_pos(position, "runner")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-05-ON-LOCATION-RUNNER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + On Location + Status Inisiasi '-' + Runner + Fisik + Inaktif.",
        }

    # A6 — ACC: ELARCH + Registrasi Masuk + '-' + Command Center + Fisik + Inaktif
    if (
        source == "elarch"
        and status == "registrasi masuk"
        and _is_init(init, "-")
        and _is_pos(position, "command center")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-06-REGISTRASI-MASUK-COMMAND-CENTER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Registrasi Masuk + Status Inisiasi '-' + Command Center + Fisik + Inaktif.",
        }

    # A7 — ACC: prefix Status Registrasi Ditolak Command Center + '-' +
    # posisi kosong + Fisik + Inaktif.
    if (
        source == "elarch"
        and _status_starts_with(status, "ditolak command center")
        and _is_init(init, "-")
        and _is_pos(position, "")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-07-DITOLAK-COMMAND-CENTER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Status Registrasi prefix 'Ditolak Command Center' + Status Inisiasi '-' + Posisi Data kosong + Fisik + Inaktif.",
        }

    # A8 — ACC: ELARCH + Registrasi Masuk Lanjutan + Diverifikasi Unit Umum
    # + Command Center + Fisik + Inaktif.
    if (
        source == "elarch"
        and status == "registrasi masuk lanjutan"
        and _is_init(init, "diverifikasi unit umum")
        and _is_pos(position, "command center")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-08-REGISTRASI-MASUK-LANJUTAN-COMMAND-CENTER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Registrasi Masuk Lanjutan + Diverifikasi Unit Umum + Command Center + Fisik + Inaktif.",
        }

    # A9 — ACC: ELARCH + Diarsipkan + Diverifikasi Unit Umum + Record Center
    # + Fisik + Inaktif. Formula Yes is still kept first; this rule is only a
    # fallback for the manually overridden records in this pattern.
    if (
        source == "elarch"
        and status == "diarsipkan"
        and _is_init(init, "diverifikasi unit umum")
        and _is_pos(position, "record center")
        and fmt == "fisik"
        and doc == "inaktif"
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-09-DIARSIPKAN-DIVERIFIKASI-UMUM-RECORD-CENTER-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif.",
        }

    # A10 — ACC exception: ELARCH + Diarsipkan + '-' + Record Center +
    # Digital + Inaktif, with the named inactive-scheduling and pickup-schedule
    # fields populated. No Excel column-letter dependency.
    if (
        source == "elarch"
        and status == "diarsipkan"
        and _is_init(init, "-")
        and _is_pos(position, "record center")
        and fmt == "digital"
        and doc == "inaktif"
        and _has_pair(row, "tanggal_penjadwalan_inaktif", "jam_penjadwalan_inaktif")
        and _has_pair(row, "tanggal_jadwal_penjemputan", "jam_jadwal_penjemputan")
    ):
        return {
            "result": "Yes",
            "rule_code": "MC-SLA2A-10-DIARSIPKAN-RECORD-CENTER-DIGITAL-INAKTIF",
            "reason": "Pola SLA 2A ACC: ELARCH + Diarsipkan + Status Inisiasi '-' + Record Center + Digital + Inaktif, dengan Tanggal/Jam Penjadwalan Arsip Inaktif dan Tanggal/Jam Jadwal Penjemputan terisi.",
        }

    return {
        "result": "N/A",
        "rule_code": None,
        "reason": "Tidak ditemukan pola manual SLA 2A yang telah di-ACC.",
    }


def apply_sla2b_manual_check(row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply only the approved SLA 2B manual patterns."""
    if not _period_gate(row, context, "2B"):
        return _blocked_period_result("SLA 2B")

    source = _canon_text(row.get("sumber"))
    status = _canon_text(row.get("status_registrasi"))
    init = _canon_text(row.get("status_inisiasi"))
    position = _canon_text(row.get("posisi_data"))
    fmt = _canon_text(row.get("format_arsip"))
    doc = _canon_text(row.get("document_type"))

    # Approved SLA 2B patterns require Tanggal/Jam Penjadwalan Arsip Inaktif 2.
    if _has_pair(row, "tanggal_penjadwalan_inaktif_2", "jam_penjadwalan_inaktif_2"):
        if source == "elarch" and status == "pickup failed" and fmt == "fisik" and doc == "inaktif":
            return {"result": "Yes", "rule_code": "MC-SLA2B-01-PICKUP-FAILED", "reason": "Pola SLA 2B ACC #1; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "diarsipkan"
            and _is_init(init, "-")
            and _is_pos(position, "record center")
            and fmt == "fisik"
            and doc == "inaktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-02-DIARSIPKAN-RECORD-CENTER-INAKTIF", "reason": "Pola SLA 2B ACC #2; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "ready to pick up"
            and _is_init(init, "-")
            and _is_pos(position, "runner")
            and fmt == "fisik"
            and doc == "inaktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-03-READY-TO-PICKUP-RUNNER-INAKTIF", "reason": "Pola SLA 2B ACC #3; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "scheduled"
            and _is_init(init, "diverifikasi unit umum")
            and _is_pos(position, "msb / unit fungsi", "msb/unit fungsi")
            and fmt == "fisik"
            and doc == "aktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-04-SCHEDULED-MSB-UNIT-FUNGSI-AKTIF", "reason": "Pola SLA 2B ACC #4; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "scheduled"
            and _is_init(init, "-")
            and _is_pos(position, "msb / unit fungsi", "msb/unit fungsi")
            and fmt == "fisik"
            and doc == "inaktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-05-SCHEDULED-MSB-UNIT-FUNGSI-INAKTIF", "reason": "Pola SLA 2B ACC #5; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if source == "elarch" and status == "on location" and _is_pos(position, "runner") and fmt == "fisik" and doc == "inaktif":
            return {"result": "Yes", "rule_code": "MC-SLA2B-06-ON-LOCATION-RUNNER-INAKTIF", "reason": "Pola SLA 2B ACC #6; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "diarsipkan"
            and _is_init(init, "diverifikasi unit umum")
            and _is_pos(position, "record center")
            and fmt == "fisik"
            and doc == "inaktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-07-DIARSIPKAN-RECORD-CENTER-DIVERIFIKASI-UMUM", "reason": "Pola SLA 2B ACC #7; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "ready to pick up"
            and _is_init(init, "diverifikasi unit umum")
            and _is_pos(position, "runner")
            and fmt == "fisik"
            and doc == "aktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-08-READY-TO-PICKUP-RUNNER-AKTIF", "reason": "Pola SLA 2B ACC #8; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        if (
            source == "elarch"
            and status == "on location"
            and _is_init(init, "diverifikasi unit umum")
            and _is_pos(position, "runner")
            and fmt == "fisik"
            and doc == "aktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-09-ON-LOCATION-RUNNER-AKTIF", "reason": "Pola SLA 2B ACC #9; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

        # New approved pattern: VIP + Diarsipkan + Diverifikasi Unit Umum
        # + Record Center + Fisik + Inaktif.
        if (
            source == "vip"
            and status == "diarsipkan"
            and _is_init(init, "diverifikasi unit umum")
            and _is_pos(position, "record center")
            and fmt == "fisik"
            and doc == "inaktif"
        ):
            return {"result": "Yes", "rule_code": "MC-SLA2B-10-VIP-DIARSIPKAN-RECORD-CENTER-INAKTIF", "reason": "Pola SLA 2B ACC tambahan: VIP + Diarsipkan + Diverifikasi Unit Umum + Record Center + Fisik + Inaktif; Tanggal/Jam Penjadwalan Arsip Inaktif 2 terisi."}

    # Explicitly do not code the pending Ditolak Command Center special case.
    return {
        "result": "N/A",
        "rule_code": None,
        "reason": "Tidak ditemukan pola manual SLA 2B yang telah di-ACC; exception Ditolak Command Center yang masih menunggu mentor tetap tidak di-override.",
    }


# Backward-compatible wrapper for callers/tests that still expect a single
# combined manual check. The main calculator now calls the branch-specific
# functions so SLA 2A and SLA 2B use their own Period Gate.
def apply_sla2_manual_check(row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    result_b = apply_sla2b_manual_check(row, context)
    if result_b.get("result") == "Yes":
        return result_b
    result_a = apply_sla2a_manual_check(row, context)
    return result_a
