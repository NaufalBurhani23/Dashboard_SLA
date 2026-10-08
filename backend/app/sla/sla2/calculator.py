from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, Optional

from app.sla.sla2.manual_rules import apply_sla2a_manual_check, apply_sla2b_manual_check


class SLA2Calculator:
    SLA_NAME = "SLA 2"
    CUTOFF_DEFAULT = time(10, 0)

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
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

    @staticmethod
    def _as_time(value: Any) -> Optional[time]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.time()
        if isinstance(value, time):
            return value
        if isinstance(value, (int, float)) and 0 <= float(value) < 1:
            seconds = round(float(value) * 86400)
            return (datetime.min + timedelta(seconds=seconds)).time()
        text = str(value).strip()
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                pass
        return None

    @classmethod
    def networkdays(cls, start: Optional[date], end: Optional[date], holidays: Iterable[date]) -> int:
        """NETWORKDAYS equivalent for the SLA formulas.

        Excel's SLA formulas have no explicit START > END guard. Returning 0
        for an inverted interval preserves the effective formula outcome after
        the mandatory -1 offset (which is still <= the SLA threshold).
        """
        if start is None or end is None or start > end:
            return 0
        holiday_set = set(holidays or [])
        days = 0
        cur = start
        while cur <= end:
            if cur.weekday() < 5 and cur not in holiday_set:
                days += 1
            cur += timedelta(days=1)
        return days

    @classmethod
    def _period_gate_2a(cls, p: date, context: Dict[str, Any]) -> bool:
        h5, h6, h8, h9 = context["h5"], context["h6"], context["h8"], context["h9"]
        return (p >= h9 or p <= h8) and (p < h6 and p != h5)

    @classmethod
    def _period_gate_2b(cls, p: date, context: Dict[str, Any]) -> bool:
        h5, h6, h8, h9 = context["h5"], context["h6"], context["h8"], context["h9"]
        return (p >= h9 or p == h8) and (p < h6 and p != h5)

    @classmethod
    def evaluate_sla_2a(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        format_arsip = cls._norm(row.get("format_arsip"))
        document_type = cls._norm(row.get("document_type"))
        tanggal_registrasi = cls._as_date(row.get("tanggal_registrasi"))
        tanggal_verifikasi_uf = cls._as_date(row.get("tanggal_verifikasi_uf"))
        tanggal_verifikasi_uu = cls._as_date(row.get("tanggal_verifikasi_uu"))
        tanggal_penjadwalan_inaktif = cls._as_date(row.get("tanggal_penjadwalan_inaktif"))
        jam_registrasi = cls._as_time(row.get("jam_registrasi"))
        jam_penjadwalan_inaktif = cls._as_time(row.get("jam_penjadwalan_inaktif"))
        status_registrasi = row.get("status_registrasi")

        if format_arsip != "fisik":
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Format Arsip bukan Fisik."}
        if not (document_type == "inaktif" or (document_type == "aktif" and tanggal_penjadwalan_inaktif is not None and jam_penjadwalan_inaktif is not None)):
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Document Type tidak memenuhi gate Inaktif atau Aktif dengan Tanggal/Jam Penjadwalan Arsip Inaktif terisi."}
        if tanggal_registrasi is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Tanggal Registrasi tidak tersedia."}

        context["registration_date"] = tanggal_registrasi
        if not cls._period_gate_2a(tanggal_registrasi, context):
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Tanggal Registrasi berada di luar period gate."}

        # Keep the Excel behavior under review #5 unchanged for now.
        # All source fields are addressed by semantic header names.
        if tanggal_registrasi is None or jam_registrasi is None or tanggal_penjadwalan_inaktif is None or jam_penjadwalan_inaktif is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Tanggal/Jam Registrasi dan Tanggal/Jam Penjadwalan Arsip Inaktif harus lengkap."}

        status_registrasi_normalized = cls._norm(status_registrasi)
        if tanggal_verifikasi_uf is None and tanggal_verifikasi_uu is None and (
            status_registrasi_normalized == "disesuaikan command center" or "permohonan" in status_registrasi_normalized
        ):
            return {"result": "N/A", "working_days": None, "reason": "SLA 2A: Tanggal Verifikasi UF/UU kosong dan Status Registrasi = Disesuaikan Command Center atau mengandung Permohonan."}

        start_date = tanggal_verifikasi_uu if tanggal_verifikasi_uu is not None else (tanggal_verifikasi_uf if tanggal_verifikasi_uf is not None else tanggal_registrasi)
        if start_date is None or tanggal_penjadwalan_inaktif is None:
            return {"result": "No", "working_days": None, "reason": "SLA 2A: START atau Tanggal Penjadwalan Arsip Inaktif tidak lengkap."}

        working_days = cls.networkdays(start_date, tanggal_penjadwalan_inaktif, context.get("holidays", [])) - 1
        if working_days <= 2:
            return {"result": "Yes", "working_days": working_days, "reason": f"SLA 2A: NETWORKDAYS(START, Tanggal Penjadwalan Arsip Inaktif)-1 = {working_days} <= 2."}
        return {"result": "No", "working_days": working_days, "reason": f"SLA 2A: NETWORKDAYS(START, Tanggal Penjadwalan Arsip Inaktif)-1 = {working_days} > 2."}

    @classmethod
    def _evaluate_2b_path(cls, path_name: str, start: date, end: date, end_time: Optional[time], cutoff: time, holidays: Iterable[date]) -> Dict[str, Any]:
        working_days = cls.networkdays(start, end, holidays) - 1
        if working_days < 2:
            return {"result": "Yes", "working_days": working_days, "reason": f"SLA 2B: jalur {path_name}; NETWORKDAYS(START, AJ)-1 = {working_days} < 2."}
        if working_days == 2:
            if (end_time or time(0)) <= cutoff:
                return {"result": "Yes", "working_days": working_days, "reason": f"SLA 2B: jalur {path_name}; working days = 2 dan Jam Penjadwalan Arsip Inaktif 2 <= cutoff {cutoff.strftime('%H:%M')}."}
            return {"result": "No", "working_days": working_days, "reason": f"SLA 2B: jalur {path_name}; working days = 2 tetapi jam AK melewati cutoff {cutoff.strftime('%H:%M')}."}
        return {"result": "No", "working_days": working_days, "reason": f"SLA 2B: jalur {path_name}; working days = {working_days} > 2."}

    @classmethod
    def evaluate_sla_2b(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        format_arsip = cls._norm(row.get("format_arsip"))
        document_type = cls._norm(row.get("document_type"))
        tanggal_registrasi = cls._as_date(row.get("tanggal_registrasi"))
        tanggal_registrasi_2 = cls._as_date(row.get("tanggal_registrasi_2"))
        tanggal_gagal_penjemputan = cls._as_date(row.get("tanggal_gagal_penjemputan"))
        tanggal_penolakan_jadwal_penjemputan = cls._as_date(row.get("tanggal_penolakan_jadwal_penjemputan"))
        tanggal_penjadwalan_inaktif_2 = cls._as_date(row.get("tanggal_penjadwalan_inaktif_2"))
        jam_penjadwalan_inaktif_2 = cls._as_time(row.get("jam_penjadwalan_inaktif_2"))

        if format_arsip != "fisik":
            return {"result": "N/A", "working_days": None, "reason": "SLA 2B: Format Arsip bukan Fisik."}
        if not (document_type == "inaktif" or (document_type == "aktif" and cls._as_date(row.get("tanggal_penjadwalan_inaktif")) is not None and cls._as_time(row.get("jam_penjadwalan_inaktif")) is not None)):
            return {"result": "N/A", "working_days": None, "reason": "SLA 2B: Document Type tidak memenuhi gate Inaktif atau Aktif dengan Tanggal/Jam Penjadwalan Arsip Inaktif terisi."}
        if tanggal_registrasi is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 2B: Tanggal Registrasi tidak tersedia."}

        context["registration_date"] = tanggal_registrasi
        if not cls._period_gate_2b(tanggal_registrasi, context):
            return {"result": "N/A", "working_days": None, "reason": "SLA 2B: Tanggal Registrasi berada di luar period gate."}

        cutoff = context.get("sla2_cutoff") or cls.CUTOFF_DEFAULT
        if tanggal_registrasi_2 is not None and tanggal_penjadwalan_inaktif_2 is not None and jam_penjadwalan_inaktif_2 is not None:
            return cls._evaluate_2b_path(
                "Tanggal Registrasi 2 -> Tanggal Penjadwalan Arsip Inaktif 2",
                tanggal_registrasi_2, tanggal_penjadwalan_inaktif_2, jam_penjadwalan_inaktif_2, cutoff, context.get("holidays", [])
            )

        jam_gagal_penjemputan = cls._as_time(row.get("jam_gagal_penjemputan"))
        if tanggal_gagal_penjemputan is not None and jam_gagal_penjemputan is not None and tanggal_penjadwalan_inaktif_2 is not None and jam_penjadwalan_inaktif_2 is not None:
            return cls._evaluate_2b_path(
                "Tanggal Gagal Penjemputan -> Tanggal Penjadwalan Arsip Inaktif 2",
                tanggal_gagal_penjemputan, tanggal_penjadwalan_inaktif_2, jam_penjadwalan_inaktif_2, cutoff, context.get("holidays", [])
            )

        jam_penolakan_jadwal_penjemputan = cls._as_time(row.get("jam_penolakan_jadwal_penjemputan"))
        if tanggal_penolakan_jadwal_penjemputan is not None and jam_penolakan_jadwal_penjemputan is not None and tanggal_penjadwalan_inaktif_2 is not None and jam_penjadwalan_inaktif_2 is not None:
            return cls._evaluate_2b_path(
                "Tanggal Penolakan Jadwal Penjemputan -> Tanggal Penjadwalan Arsip Inaktif 2",
                tanggal_penolakan_jadwal_penjemputan, tanggal_penjadwalan_inaktif_2, jam_penjadwalan_inaktif_2, cutoff, context.get("holidays", [])
            )
        return {"result": "N/A", "working_days": None, "reason": "SLA 2B: tidak ada jalur tanggal/jam yang lengkap sesuai urutan proses vendor."}

    @classmethod
    def evaluate_vendor(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """RAW -> header mapping -> SLA 2A + SLA 2B -> approved manual override -> final.

        Unlike SLA 1's serial short-circuit, SLA 2A and SLA 2B are both
        evaluated because Excel has two parallel formula columns. The final
        SLA 2 result is Yes when either formula is Yes.
        """
        a = cls.evaluate_sla_2a(row, context)
        b = cls.evaluate_sla_2b(row, context)
        a_result, b_result = a["result"], b["result"]

        if a_result == "Yes" or b_result == "Yes":
            selected = a if a_result == "Yes" else b
            source = "SLA 2A" if a_result == "Yes" else "SLA 2B"
            # For audit we keep the complete parallel formula result.
            return {
                "result": "Yes",
                "sla_2a_result": a_result,
                "sla_2b_result": b_result,
                "manual_result": "N/A",
                "decision_source": source,
                "manual_rule": None,
                "working_days": selected.get("working_days"),
                "sla_2a_working_days": a.get("working_days"),
                "sla_2b_working_days": b.get("working_days"),
                "reason": f"SLA 2 Final = Yes karena SLA 2A={a_result} atau SLA 2B={b_result}.",
                "flow_stage": "FORMULA_YES",
            }

        # Manual rules are evaluated per branch only after both formula paths
        # have run. This keeps SLA 2A and SLA 2B on their exact Period Gate and
        # prevents the pending SLA 2B out-of-period cases from being resurrected
        # by an SLA 2A-style union gate.
        manual_a = apply_sla2a_manual_check(row, context) if a_result != "Yes" else {"result": "N/A", "rule_code": None, "reason": "SLA 2A formula sudah Yes."}
        manual_b = apply_sla2b_manual_check(row, context) if b_result != "Yes" else {"result": "N/A", "rule_code": None, "reason": "SLA 2B formula sudah Yes."}
        manual_a_yes = manual_a.get("result") == "Yes"
        manual_b_yes = manual_b.get("result") == "Yes"

        if manual_a_yes or manual_b_yes:
            matched = [m for m in (manual_a, manual_b) if m.get("result") == "Yes"]
            rule_codes = [m.get("rule_code") for m in matched if m.get("rule_code")]
            reasons = [m.get("reason") for m in matched if m.get("reason")]
            if manual_a_yes and manual_b_yes:
                decision_source = "MANUAL SLA 2A + SLA 2B"
            elif manual_a_yes:
                decision_source = "MANUAL SLA 2A"
            else:
                decision_source = "MANUAL SLA 2B"
            return {
                "result": "Yes",
                "sla_2a_result": a_result,
                "sla_2b_result": b_result,
                "manual_result": "Yes",
                "decision_source": decision_source,
                "manual_rule": " | ".join(rule_codes) if rule_codes else None,
                "working_days": None,
                "sla_2a_working_days": a.get("working_days"),
                "sla_2b_working_days": b.get("working_days"),
                "reason": " ".join(reasons),
                "flow_stage": "MANUAL_OVERRIDE_MATCH",
            }

        final = "No" if a_result == "No" or b_result == "No" else "N/A"
        return {
            "result": final,
            "sla_2a_result": a_result,
            "sla_2b_result": b_result,
            "manual_result": "N/A",
            "decision_source": "FORMULA_NO_AFTER_MANUAL_MISS" if final == "No" else "FINAL_NA_AFTER_MANUAL_MISS",
            "manual_rule": None,
            "working_days": b.get("working_days") if b_result == "No" else a.get("working_days"),
            "sla_2a_working_days": a.get("working_days"),
            "sla_2b_working_days": b.get("working_days"),
            "reason": f"SLA 2 Final = {final}; SLA 2A={a_result}, SLA 2B={b_result}, manual SLA 2A={manual_a.get("result")}, manual SLA 2B={manual_b.get("result") }.",
            "flow_stage": "FINAL_NO" if final == "No" else "FINAL_NA",
        }

    @staticmethod
    def to_dashboard_status(result: str) -> str:
        return {"Yes": "ON TIME", "No": "OUT OF DATE", "N/A": "INCOMPLETE"}.get(result, "INCOMPLETE")
