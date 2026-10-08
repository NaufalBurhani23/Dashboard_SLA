from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, Optional
from app.sla.sla1.manual_rules import apply_vendor_manual_check


class SLA1Calculator:
    SLA_NAME = "SLA 1"
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
    def networkdays(cls, start: date, end: date, holidays: Iterable[date]) -> int:
        if start > end:
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
        """Return True when registration is outside the SLA registration window.

        The vendor formula uses H5/H6/H8/H9. In project terminology those
        references mean: current month Hari Kerja Terakhir Hari ke-1/ke-2
        and previous month Hari Kerja Terakhir Hari ke-1/ke-2. They are ordinal
        labels, not date subtraction operations.
        """
        current_day_1 = context["current_last_working_day_1"]  # H-1, month berjalan
        current_day_2 = context["current_last_working_day_2"]  # H-2, month berjalan
        previous_day_1 = context["previous_last_working_day_1"]  # H-1, bulan sebelumnya
        previous_day_2 = context["previous_last_working_day_2"]  # H-2, bulan sebelumnya
        return not ((p >= previous_day_2 or p <= previous_day_1) and (p < current_day_2 and p != current_day_1))

    @classmethod
    def evaluate_sla_1a(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        m = cls._norm(row.get("format_arsip"))
        n = cls._norm(row.get("document_type"))
        p = cls._as_date(row.get("tanggal_registrasi"))
        q = cls._as_time(row.get("jam_registrasi"))
        r = cls._as_date(row.get("tanggal_verifikasi_uf"))
        s = cls._as_time(row.get("jam_verifikasi_uf"))
        t = cls._as_date(row.get("tanggal_verifikasi_uu"))
        u = cls._as_time(row.get("jam_verifikasi_uu"))
        v = cls._as_date(row.get("tanggal_verifikasi_arsip"))
        w = cls._as_time(row.get("jam_verifikasi_arsip"))

        if m not in {"fisik", "digital"}:
            return {"result": "N/A", "working_days": None, "reason": "Format Arsip bukan fisik/digital."}
        if m != "digital" and n != "aktif":
            return {"result": "N/A", "working_days": None, "reason": "Format fisik dengan Document Type bukan aktif."}
        if p is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal Registrasi tidak tersedia."}
        if cls._period_gate(p, context):
            return {"result": "N/A", "working_days": None, "reason": "Tanggal Registrasi berada di luar periode SLA 1A."}
        if (v is None and w is None):
            return {"result": "N/A", "working_days": None, "reason": "Tanggal dan Jam Verifikasi Arsip kosong."}
        if t is None and u is None and r is None and s is None and "permohonan" in cls._norm(row.get("nama_dokumen")):
            return {"result": "N/A", "working_days": None, "reason": "T/U dan R/S kosong serta Nama Dokumen/Hal mengandung Permohonan."}

        use_tu = False
        tu_days = None
        if t is not None and u is not None and v is not None:
            tu_days = cls.networkdays(t, v, context["holidays"]) - 1
            use_tu = tu_days >= 0

        if use_tu:
            start_date, start_time = t, u
            start_source = "T/U"
        elif r is not None and s is not None:
            start_date, start_time = r, s
            start_source = "R/S"
        else:
            start_date, start_time = p, q
            start_source = "P/Q"

        if v is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal Verifikasi Arsip tidak tersedia untuk perhitungan."}
        if start_date > v:
            return {"result": "No", "working_days": None, "reason": f"START {start_source} lebih besar dari END Verifikasi Arsip."}
        if start_date == v and (w or time(0)) < (start_time or time(0)):
            return {"result": "No", "working_days": None, "reason": f"Tanggal START dan END sama tetapi jam END lebih kecil dari START {start_source}."}

        working_days = cls.networkdays(start_date, v, context["holidays"]) - 1
        cutoff = context.get("cutoff") or cls.CUTOFF_DEFAULT
        if working_days <= 1:
            return {"result": "Yes", "working_days": working_days, "reason": f"NETWORKDAYS(START={start_source}, END=V)-1 = {working_days} <= 1."}
        if working_days == 2 and (w or time(0)) <= cutoff:
            return {"result": "Yes", "working_days": working_days, "reason": f"Working days = 2 dan Jam Verifikasi Arsip <= cutoff {cutoff.strftime('%H:%M')}."}
        return {"result": "No", "working_days": working_days, "reason": f"Working days = {working_days} dan tidak memenuhi cutoff SLA 1A."}

    @classmethod
    def evaluate_sla_1b(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        m = cls._norm(row.get("format_arsip"))
        n = cls._norm(row.get("document_type"))
        p = cls._as_date(row.get("tanggal_registrasi"))
        z = cls._as_date(row.get("tanggal_registrasi_2"))
        aa = cls._as_time(row.get("jam_registrasi_2"))
        v = cls._as_date(row.get("tanggal_verifikasi_arsip"))
        w = cls._as_time(row.get("jam_verifikasi_arsip"))
        ab = cls._as_date(row.get("tanggal_verifikasi_arsip_2"))
        ac = cls._as_time(row.get("jam_verifikasi_arsip_2"))

        if m not in {"fisik", "digital"}:
            return {"result": "N/A", "working_days": None, "reason": "Format Arsip bukan fisik/digital."}
        if m != "digital" and n != "aktif":
            return {"result": "N/A", "working_days": None, "reason": "Format fisik dengan Document Type bukan aktif."}
        if p is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal Registrasi tidak tersedia."}
        previous_day_1 = context["previous_last_working_day_1"]
        previous_day_2 = context["previous_last_working_day_2"]
        current_day_1 = context["current_last_working_day_1"]
        current_day_2 = context["current_last_working_day_2"]
        if not ((p >= previous_day_2 or p == previous_day_1) and (p < current_day_2 and p != current_day_1)):
            return {"result": "N/A", "working_days": None, "reason": "Tanggal Registrasi berada di luar periode SLA 1B."}
        if z is None and aa is None and ab is None and ac is None and context.get("cutoff") is None:
            return {"result": "N/A", "working_days": None, "reason": "Seluruh field proses SLA 1B dan cutoff kosong."}
        if z is None and aa is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal/Jam Registrasi 2 kosong."}
        if v is None and w is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal/Jam Verifikasi Arsip pertama kosong."}
        if ab is None and ac is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal/Jam Verifikasi Arsip 2 kosong."}
        if z is None or ab is None:
            return {"result": "N/A", "working_days": None, "reason": "Tanggal START/END SLA 1B tidak lengkap."}
        if z == ab and (ac or time(0)) < (aa or time(0)):
            return {"result": "No", "working_days": None, "reason": "Tanggal START dan END sama tetapi jam END 2 lebih kecil dari START 2."}

        working_days = cls.networkdays(z, ab, context["holidays"]) - 1
        cutoff = context.get("cutoff") or cls.CUTOFF_DEFAULT
        if working_days <= 1:
            return {"result": "Yes", "working_days": working_days, "reason": f"NETWORKDAYS(Registrasi 2, Verifikasi Arsip 2)-1 = {working_days} <= 1."}
        if working_days == 2 and (ac or time(0)) <= cutoff:
            return {"result": "Yes", "working_days": working_days, "reason": f"Working days = 2 dan Jam Verifikasi Arsip 2 <= cutoff {cutoff.strftime('%H:%M')}."}
        return {"result": "No", "working_days": working_days, "reason": f"Working days = {working_days} dan tidak memenuhi cutoff SLA 1B."}

    @classmethod
    def evaluate_vendor(cls, row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the agreed SLA 1 decision flow.

        RAW DATA -> header mapping -> SLA 1A -> SLA 1B -> manual override.
        Only a formula result of YES short-circuits the flow. NO and N/A
        continue to the next stage. After SLA 1B, manual override is checked.
        If override matches, final is YES. If it does not match, the final
        result is NO when either formula produced NO; otherwise N/A.
        """
        a = cls.evaluate_sla_1a(row, context)
        a_result = a["result"]

        # SLA 1A YES is immediately the final result.
        if a_result == "Yes":
            return {
                "result": "Yes",
                "sla_1a_result": "Yes",
                "sla_1b_result": "N/A",
                "decision_source": "SLA 1A",
                "manual_rule": None,
                "working_days": a.get("working_days"),
                "reason": a.get("reason"),
                "flow_stage": "SLA_1A_YES",
            }

        # SLA 1A NO or N/A both continue to SLA 1B.
        b = cls.evaluate_sla_1b(row, context)
        b_result = b["result"]

        # SLA 1B YES is immediately the final result.
        if b_result == "Yes":
            return {
                "result": "Yes",
                "sla_1a_result": a_result,
                "sla_1b_result": "Yes",
                "decision_source": "SLA 1B",
                "manual_rule": None,
                "working_days": b.get("working_days"),
                "reason": b.get("reason"),
                "flow_stage": "SLA_1B_YES",
            }

        # Both formula paths failed to produce YES, so run manual override.
        manual = apply_vendor_manual_check(row, context)
        manual_result = manual.get("result", "N/A")

        if manual_result == "Yes":
            return {
                "result": "Yes",
                "sla_1a_result": a_result,
                "sla_1b_result": b_result,
                "decision_source": "MANUAL VENDOR RULE",
                "manual_rule": manual.get("rule_code"),
                "working_days": None,
                "reason": manual.get("reason"),
                "flow_stage": "MANUAL_OVERRIDE_MATCH",
            }

        # Manual override did not match: any formula NO makes final NO.
        if a_result == "No" or b_result == "No":
            return {
                "result": "No",
                "sla_1a_result": a_result,
                "sla_1b_result": b_result,
                "decision_source": "FORMULA_NO_AFTER_MANUAL_MISS",
                "manual_rule": manual.get("rule_code"),
                "working_days": b.get("working_days") if b_result == "No" else a.get("working_days"),
                "reason": f"Manual override tidak match; hasil formula: SLA 1A={a_result}, SLA 1B={b_result}.",
                "flow_stage": "FINAL_NO",
            }

        # Neither formula produced NO and manual did not match -> N/A.
        return {
            "result": "N/A",
            "sla_1a_result": a_result,
            "sla_1b_result": b_result,
            "decision_source": "FINAL_NA_AFTER_MANUAL_MISS",
            "manual_rule": manual.get("rule_code"),
            "working_days": None,
            "reason": f"Manual override tidak match; SLA 1A={a_result}, SLA 1B={b_result}, dan tidak ada hasil No.",
            "flow_stage": "FINAL_NA",
        }

    @staticmethod
    def to_dashboard_status(result: str) -> str:
        return {"Yes": "ON TIME", "No": "OUT OF DATE", "N/A": "INCOMPLETE"}.get(result, "INCOMPLETE")
