"""Validated manual fallback rules for SLA 1.

Important business rule:
- SLA 1A and SLA 1B are evaluated first.
- Manual rules are a fallback only after both formula paths have failed
  to produce ``Yes``.
- A manual rule is never allowed to bypass the SLA registration-window guard.
- The four operational columns (Sumber, Status Registrasi, Status Inisiasi,
  Posisi Data) identify a candidate pattern, but the relevant raw workflow
  fields are still checked before a manual ``Yes`` is returned.
- Only ``Yes``, ``No`` and ``N/A`` are valid SLA status values. Manual rules
  themselves return ``Yes`` or ``N/A``; they never manufacture a separate
  business status.
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


def _format_document_allowed(row: Dict[str, Any]) -> bool:
    fmt = _norm(row.get("format_arsip"))
    doc = _norm(row.get("document_type"))
    # SLA 1: digital can be active/inactive; physical must be active.
    return fmt == "digital" or (fmt == "fisik" and doc == "aktif")


def _registration_window_is_manual_eligible(row: Dict[str, Any], context: Dict[str, Any]) -> tuple[bool, str]:
    """Prevent manual rules from resurrecting late-period registrations.

    For the August 2026 vendor period, the final two working registration
    days are 28 Aug (H-2 = Hari Kerja Terakhir Hari ke-2) and 31 Aug
    (H-1 = Hari Kerja Terakhir Hari ke-1). These days are deliberately
    excluded from manual override because the vendor treats them as outside
    the registration window for the SLA calculation. The same ordinal rule is
    derived from the supplied period context for other months.
    """
    p = _as_date(row.get("tanggal_registrasi"))
    if p is None:
        return False, "Tanggal Registrasi tidak tersedia; manual override diblokir."

    period_label = str(context.get("period_label") or "")
    try:
        period_year, period_month = int(period_label[:4]), int(period_label[5:7])
    except (TypeError, ValueError):
        period_year = p.year
        period_month = p.month

    day_1 = context.get("current_last_working_day_1")
    day_2 = context.get("current_last_working_day_2")

    # Explicitly block the two final working registration days in the
    # reporting month. H-1/H-2 are ordinal labels: Hari Kerja Terakhir
    # Hari ke-1 and Hari ke-2, not subtraction from a date.
    if p.year == period_year and p.month == period_month and p in {day_1, day_2}:
        late_label = (
            "H-1 (Hari Kerja Terakhir Hari ke-1)"
            if p == day_1
            else "H-2 (Hari Kerja Terakhir Hari ke-2)"
        )
        return False, f"Tanggal Registrasi {p.isoformat()} adalah {late_label}; manual override tidak boleh melewati batas registrasi SLA."

    return True, "Tanggal Registrasi masih berada pada jendela yang diizinkan untuk manual fallback."


# These are the inactive-document workflow fields observed in the raw August
# workbook. Any populated field means the record has progressed into an
# inactive-archive operational path and must not be collapsed into the generic
# Digital + Inaktif + Record Center manual-Yes pattern.
INACTIVE_WORKFLOW_FIELDS = (
    "tanggal_penjadwalan_inaktif",
    "jam_penjadwalan_inaktif",
    "tanggal_jadwal_penjemputan",
    "jam_jadwal_penjemputan",
    "tanggal_penjemputan_dokumen",
    "jam_penjemputan_dokumen",
    "tanggal_runner_record_center",
    "jam_runner_record_center",
    "tanggal_registrasi_arsip_generate_barcode",
    "jam_registrasi_arsip_generate_barcode",
)


def _inactive_workflow_present(row: Dict[str, Any]) -> bool:
    return any(not _empty(row.get(key)) for key in INACTIVE_WORKFLOW_FIELDS)


def _guarded_manual_yes(
    *,
    rule_code: str,
    reason: str,
    row: Dict[str, Any],
    context: Dict[str, Any],
    reject_inactive_workflow: bool = False,
    block_late_registration: bool = False,
) -> Dict[str, Any]:
    if not _format_document_allowed(row):
        return {
            "result": "N/A",
            "rule_code": "MC-SLA1-GUARD-FORMAT-DOCUMENT",
            "reason": "Kandidat manual override ditolak karena Format Arsip/Document Type tidak memenuhi gate SLA 1.",
        }

    if block_late_registration:
        ok, window_reason = _registration_window_is_manual_eligible(row, context)
        if not ok:
            return {
                "result": "N/A",
                "rule_code": "MC-SLA1-GUARD-REGISTRATION-WINDOW",
                "reason": window_reason,
            }

    if reject_inactive_workflow and _inactive_workflow_present(row):
        return {
            "result": "N/A",
            "rule_code": "MC-SLA1-GUARD-INACTIVE-WORKFLOW",
            "reason": "Kandidat manual override ditolak karena tahapan Arsip Inaktif (penjadwalan/penjemputan/runner/generate barcode) sudah terisi.",
        }

    return {
        "result": "Yes",
        "rule_code": rule_code,
        "reason": reason,
    }


def _status_starts_with(value: Any, prefix: str) -> bool:
    value_n = _norm(value)
    prefix_n = _norm(prefix)
    return value_n == prefix_n or value_n.startswith(prefix_n + " ")


def apply_vendor_manual_check(row: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate only *validated* vendor-style manual fallback patterns.

    ``context`` is required by rule families that use the registration-window
    protection. It is kept optional for direct unit-test/backward compatibility.
    """
    context = context or {}

    if not _format_document_allowed(row):
        return {
            "result": "N/A",
            "rule_code": "MC-SLA1-GUARD-FORMAT-DOCUMENT",
            "reason": "Override SLA 1 tidak diterapkan karena Format Arsip/Document Type tidak memenuhi gate SLA 1.",
        }

    # Date-window protection is applied only to rule families for which the
    # August vendor result analysis established that H-2/H-1 registrations
    # (Hari Kerja Terakhir Hari ke-2/ke-1 pada bulan berjalan) must not be
    # resurrected by manual override. It is intentionally not a
    # global guard because other validated manual patterns are Yes even on
    # some late-period registration dates.

    sumber = _norm(row.get("sumber"))
    status_reg = _norm(row.get("status_registrasi"))
    status_init = _norm(row.get("status_inisiasi"))
    posisi = _norm(row.get("posisi_data"))

    # ------------------------------------------------------------------
    # ELARCH + DIARSIPKAN: only approved operational positions are allowed.
    # The inactive workflow guard is mandatory here so that a specific
    # Digital + Inaktif + Record Center row with actual pickup/runner/barcode
    # activity is NOT treated like every generic Record Center row.
    # ------------------------------------------------------------------
    if sumber == "elarch" and status_reg == "diarsipkan" and status_init == "-":
        if posisi in {"tersimpan aktif elarch", "record center", "runner"}:
            return _guarded_manual_yes(
                rule_code="MC-SLA1-ELARCH-DIARSIPKAN-POSISI",
                reason=(
                    "Formula SLA 1A dan SLA 1B tidak menghasilkan Yes; pola ELARCH + Diarsipkan + - "
                    f"+ {posisi} cocok, Format Arsip/Document Type memenuhi gate, tanggal registrasi berada "
                    "pada jendela yang diizinkan, dan seluruh field operasional Arsip Inaktif masih kosong."
                ),
                row=row,
                context=context,
                reject_inactive_workflow=True,
            )

    # ------------------------------------------------------------------
    # ELARCH + VERIFIKASI COMMAND CENTER. Prefix is intentionally exact for
    # this status family; no broad fuzzy matching beyond the operational name.
    # ------------------------------------------------------------------
    if (
        sumber == "elarch"
        and status_reg == "verifikasi command center"
        and status_init == "-"
        and posisi == ""
    ):
        return _guarded_manual_yes(
            rule_code="MC-SLA1-ELARCH-VERIFIKASI-CC",
            reason=(
                "Formula SLA 1A dan SLA 1B tidak menghasilkan Yes; empat kolom operasional cocok "
                "dengan pola ELARCH + Verifikasi Command Center."
            ),
            row=row,
            context=context,
            block_late_registration=True,
        )

    # ------------------------------------------------------------------
    # VIP + Ditolak Command Center (...) + Diverifikasi Unit Umum.
    # The real August values contain a parenthetical explanation, therefore
    # matching must use starts-with instead of exact-string equality.
    # ------------------------------------------------------------------
    if (
        sumber == "vip"
        and _status_starts_with(status_reg, "ditolak command center")
        and status_init == "diverifikasi unit umum"
        and posisi == ""
    ):
        return _guarded_manual_yes(
            rule_code="MC-SLA1-VIP-DITOLAK-CC",
            reason=(
                "Formula SLA 1A dan SLA 1B tidak menghasilkan Yes; pola VIP + Ditolak Command Center* "
                "+ Diverifikasi Unit Umum + Posisi kosong cocok dan Format Arsip/Document Type memenuhi gate."
            ),
            row=row,
            context=context,
        )

    # ------------------------------------------------------------------
    # ELARCH + Ditolak Command Center (...) + Status Inisiasi '-' + Posisi
    # kosong. This covers Fisik/Aktif, Digital/Aktif and Digital/Inaktif;
    # the format/document gate above still blocks Fisik/Inaktif.
    # ------------------------------------------------------------------
    if (
        sumber == "elarch"
        and _status_starts_with(status_reg, "ditolak command center")
        and status_init == "-"
        and posisi == ""
    ):
        return _guarded_manual_yes(
            rule_code="MC-SLA1-ELARCH-DITOLAK-CC",
            reason=(
                "Formula SLA 1A dan SLA 1B tidak menghasilkan Yes; pola ELARCH + Ditolak Command Center* "
                "+ Status Inisiasi '-' + Posisi kosong cocok."
            ),
            row=row,
            context=context,
        )

    # Scheduled / Ready To Pick Up remain explicit, not frequency-based rules.
    if (
        sumber == "elarch"
        and status_reg == "scheduled"
        and status_init == "diverifikasi unit umum"
        and posisi == "msb / unit fungsi"
    ):
        if _empty(row.get("tanggal_penjadwalan_inaktif")) and _empty(row.get("jam_penjadwalan_inaktif")):
            return _guarded_manual_yes(
                rule_code="MC-SLA1-SCHEDULED-TU-EMPTY",
                reason="Pola Scheduled tervalidasi dan Tanggal/Jam Penjadwalan Arsip Inaktif kosong.",
                row=row,
                context=context,
            )
        return {
            "result": "N/A",
            "rule_code": "MC-SLA1-GUARD-INACTIVE-SCHEDULE",
            "reason": "Pola Scheduled cocok, tetapi Tanggal/Jam Penjadwalan Arsip Inaktif sudah terisi.",
        }

    if (
        sumber == "elarch"
        and status_reg == "ready to pick up"
        and status_init == "diverifikasi unit umum"
        and posisi == "runner"
    ):
        if _empty(row.get("tanggal_penjadwalan_inaktif")) and _empty(row.get("jam_penjadwalan_inaktif")):
            return _guarded_manual_yes(
                rule_code="MC-SLA1-PICKUP-TU-EMPTY",
                reason="Pola Ready To Pick Up tervalidasi dan Tanggal/Jam Penjadwalan Arsip Inaktif kosong.",
                row=row,
                context=context,
            )
        return {
            "result": "N/A",
            "rule_code": "MC-SLA1-GUARD-INACTIVE-SCHEDULE",
            "reason": "Pola Ready To Pick Up cocok, tetapi Tanggal/Jam Penjadwalan Arsip Inaktif sudah terisi.",
        }

    return {
        "result": "N/A",
        "rule_code": None,
        "reason": "Tidak ditemukan pola override SLA 1 yang tervalidasi dari variabel raw sebelum kolom hasil.",
    }
