from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, Optional

from app.sla.sla3.manual_rules import apply_sla3_manual_check


class SLA3Calculator:
    SLA_NAME = "SLA 3"

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
        """NETWORKDAYS equivalent for the SLA formulas."""
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
    def _period_gate(cls, p: date, context: Dict[str, Any]) -> bool:
        """Menggunakan gate yang identik dengan SLA 2A."""
        h5, h6, h8, h9 = context["h5"], context["h6"], context["h8"], context["h9"]
        return (p >= h9 or p <= h8) and (p < h6 and p != h5)

    @classmethod
    def _get_threshold(cls, unit: Any) -> int:
        """Threshold 24 hari untuk KP dan Banten, sisanya 8 hari."""
        u = cls._norm(unit)
        if u in {"kantor pusat", "uid banten"}:
            return 24
        return 8

    @classmethod
    def evaluate_sla_3a(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        m = cls._norm(row.get("format_arsip"))
        n = cls._norm(row.get("document_type"))
        p = cls._as_date(row.get("tanggal_registrasi"))
        k = row.get("unit")
        
        x = cls._as_date(row.get("tanggal_penjadwalan_inaktif"))
        y = cls._as_time(row.get("jam_penjadwalan_inaktif"))
        ad = cls._as_date(row.get("tanggal_jadwal_penjemputan"))
        aj = cls._as_date(row.get("tanggal_penjadwalan_inaktif_2"))

        # Gate 1 & 2: Format Arsip Fisik, Document Type Inaktif / Aktif (dengan X & Y terisi)
        if m != "fisik":
            return {"result": "N/A", "working_days": None, "reason": "SLA 3A: Format Arsip bukan Fisik."}
        if not (n == "inaktif" or (n == "aktif" and x is not None and y is not None)):
            return {"result": "N/A", "working_days": None, "reason": "SLA 3A: Document Type tidak memenuhi gate Inaktif atau Aktif dengan X/Y terisi."}
        
        # Gate 3: Period Gate
        if p is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 3A: Tanggal Registrasi tidak tersedia."}
        
        context["registration_date"] = p
        if not cls._period_gate(p, context):
            return {"result": "N/A", "working_days": None, "reason": "SLA 3A: Tanggal Registrasi berada di luar period gate."}

        # Short-Circuit Yes: Jika kolom AJ (Tanggal Penjadwalan Arsip Inaktif 2) terisi
        if aj is not None:
            return {"result": "Yes", "working_days": None, "reason": "SLA 3A: Tanggal Penjadwalan Inaktif 2 (AJ) terisi (Short-circuit Yes)."}

        # Pastikan START dan END tersedia
        if x is None or ad is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 3A: Tanggal Penjadwalan Inaktif (X) atau Tanggal Jadwal Penjemputan (AD) kosong."}

        # Kalkulasi
        working_days = cls.networkdays(x, ad, context.get("holidays", [])) - 1
        threshold = cls._get_threshold(k)

        if working_days <= threshold:
            return {"result": "Yes", "working_days": working_days, "reason": f"SLA 3A: NETWORKDAYS(X, AD)-1 = {working_days} <= threshold {threshold} hari."}
        return {"result": "No", "working_days": working_days, "reason": f"SLA 3A: NETWORKDAYS(X, AD)-1 = {working_days} > threshold {threshold} hari."}

    @classmethod
    def evaluate_sla_3b(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        m = cls._norm(row.get("format_arsip"))
        n = cls._norm(row.get("document_type"))
        p = cls._as_date(row.get("tanggal_registrasi"))
        k = row.get("unit")
        
        x = cls._as_date(row.get("tanggal_penjadwalan_inaktif"))
        y = cls._as_time(row.get("jam_penjadwalan_inaktif"))
        ad = cls._as_date(row.get("tanggal_jadwal_penjemputan"))
        aj = cls._as_date(row.get("tanggal_penjadwalan_inaktif_2"))

        if m != "fisik":
            return {"result": "N/A", "working_days": None, "reason": "SLA 3B: Format Arsip bukan Fisik."}
        if not (n == "inaktif" or (n == "aktif" and x is not None and y is not None)):
            return {"result": "N/A", "working_days": None, "reason": "SLA 3B: Document Type tidak memenuhi gate Inaktif atau Aktif dengan X/Y terisi."}
        if p is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 3B: Tanggal Registrasi tidak tersedia."}

        context["registration_date"] = p
        if not cls._period_gate(p, context):
            return {"result": "N/A", "working_days": None, "reason": "SLA 3B: Tanggal Registrasi berada di luar period gate."}

        if aj is None or ad is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 3B: Tanggal Penjadwalan Inaktif 2 (AJ) atau Tanggal Jadwal Penjemputan (AD) kosong."}

        # Kalkulasi
        working_days = cls.networkdays(aj, ad, context.get("holidays", [])) - 1
        threshold = cls._get_threshold(k)

        if working_days <= threshold:
            return {"result": "Yes", "working_days": working_days, "reason": f"SLA 3B: NETWORKDAYS(AJ, AD)-1 = {working_days} <= threshold {threshold} hari."}
        return {"result": "No", "working_days": working_days, "reason": f"SLA 3B: NETWORKDAYS(AJ, AD)-1 = {working_days} > threshold {threshold} hari."}

    @classmethod
    def evaluate_vendor(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """RAW -> header mapping -> SLA 3A + SLA 3B -> approved manual override -> final."""
        
        a = cls.evaluate_sla_3a(row, context)
        b = cls.evaluate_sla_3b(row, context)
        a_result, b_result = a["result"], b["result"]

        # 1. Jika salah satu formula menghasilkan Yes, final otomatis Yes.
        if a_result == "Yes" or b_result == "Yes":
            selected = a if a_result == "Yes" else b
            source = "SLA 3A" if a_result == "Yes" else "SLA 3B"
            return {
                "result": "Yes",
                "sla_3a_result": a_result,
                "sla_3b_result": b_result,
                "manual_result": "N/A",
                "decision_source": source,
                "manual_rule": None,
                "working_days": selected.get("working_days"),
                "sla_3a_working_days": a.get("working_days"),
                "sla_3b_working_days": b.get("working_days"),
                "reason": f"SLA 3 Final = Yes karena SLA 3A={a_result} atau SLA 3B={b_result}.",
                "flow_stage": "FORMULA_YES",
            }

        # 2. Cek Aturan Manual Override
        manual = apply_sla3_manual_check(row, context)
        if manual.get("result") == "Yes":
            return {
                "result": "Yes",
                "sla_3a_result": a_result,
                "sla_3b_result": b_result,
                "manual_result": "Yes",
                "decision_source": "MANUAL SLA 3",
                "manual_rule": manual.get("rule_code"),
                "working_days": None,
                "sla_3a_working_days": a.get("working_days"),
                "sla_3b_working_days": b.get("working_days"),
                "reason": manual.get("reason"),
                "flow_stage": "MANUAL_OVERRIDE_MATCH",
            }

        # 3. Final Decision untuk kasus No / N/A
        final = "No" if a_result == "No" or b_result == "No" else "N/A"
        return {
            "result": final,
            "sla_3a_result": a_result,
            "sla_3b_result": b_result,
            "manual_result": manual.get("result"),
            "decision_source": "FORMULA_NO_AFTER_MANUAL_MISS" if final == "No" else "FINAL_NA_AFTER_MANUAL_MISS",
            "manual_rule": None,
            "working_days": b.get("working_days") if b_result == "No" else a.get("working_days"),
            "sla_3a_working_days": a.get("working_days"),
            "sla_3b_working_days": b.get("working_days"),
            "reason": f"SLA 3 Final = {final}; SLA 3A={a_result}, SLA 3B={b_result}, manual SLA 3={manual.get('result')}.",
            "flow_stage": "FINAL_NO" if final == "No" else "FINAL_NA",
        }

    @staticmethod
    def to_dashboard_status(result: str) -> str:
        return {"Yes": "ON TIME", "No": "OUT OF DATE", "N/A": "INCOMPLETE"}.get(result, "INCOMPLETE")