from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable


class SLA4Calculator:
    """Named-header SLA 4A/4B implementation.

    The class intentionally never references Excel column letters. The input row
    uses semantic field names supplied by services.excel_parser.py.
    """

    CUTOFF = time(23, 59)

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def _as_date(value: Any) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _as_time(value: Any) -> time | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.time()
        if isinstance(value, time):
            return value
        if isinstance(value, (float, int)) and 0 <= float(value) < 1:
            return (datetime.min + timedelta(seconds=round(float(value) * 86400))).time()
        text = str(value).strip()
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                pass
        return None

    @staticmethod
    def networkdays(start: date, end: date, holidays: Iterable[date]) -> int:
        """Excel-like NETWORKDAYS: weekends + holidays excluded, reverse range negative."""
        holiday_set = set(holidays)
        if start == end:
            return 0 if start.weekday() >= 5 or start in holiday_set else 1
        if start > end:
            return -SLA4Calculator.networkdays(end, start, holiday_set)
        count = 0
        cur = start
        while cur <= end:
            if cur.weekday() < 5 and cur not in holiday_set:
                count += 1
            cur += timedelta(days=1)
        return count

    @staticmethod
    def _last_working_days(year: int, month: int, holidays: set[date]) -> tuple[date, date, date]:
        cur = date(year, month, monthrange(year, month)[1])
        found: list[date] = []
        while len(found) < 3:
            if cur.weekday() < 5 and cur not in holidays:
                found.append(cur)
            cur -= timedelta(days=1)
        return found[0], found[1], found[2]

    @staticmethod
    def period_gate(schedule_date: date, registration_date: date | None, holidays: Iterable[date]) -> bool:
        """Vendor gate based on Tanggal Jadwal Penjemputan and report-month reference days."""
        if registration_date is None:
            return True
        period_year, period_month = registration_date.year, registration_date.month
        holiday_set = set(holidays)
        current_1, current_2, _ = SLA4Calculator._last_working_days(period_year, period_month, holiday_set)
        prev_year, prev_month = (period_year - 1, 12) if period_month == 1 else (period_year, period_month - 1)
        previous_1, previous_2, _ = SLA4Calculator._last_working_days(prev_year, prev_month, holiday_set)

        # Equivalent shape to the vendor formula, expressed only with
        # semantic fields: Tanggal Jadwal Penjemputan is compared with the
        # previous/current last-working-day reference values.
        return (
            (schedule_date == previous_1 or schedule_date >= previous_2)
            and schedule_date < current_2
            and schedule_date != current_1
        )

    @staticmethod
    def _eligible(row: dict[str, Any]) -> tuple[bool, str]:
        format_arsip = SLA4Calculator._norm(row.get("format_arsip"))
        document_type = SLA4Calculator._norm(row.get("document_type"))
        x = row.get("tanggal_penjadwalan_inaktif")
        y = row.get("jam_penjadwalan_inaktif")
        if format_arsip != "fisik":
            return False, "Format Arsip bukan Fisik."
        if document_type == "inaktif":
            return True, "Document Type Inaktif."
        if document_type == "aktif" and x is not None and y is not None:
            return True, "Document Type Aktif dengan tanggal/jam penjadwalan arsip inaktif lengkap."
        return False, "Document Type tidak memenuhi gate Inaktif atau Aktif + penjadwalan inaktif lengkap."

    @staticmethod
    def _same_day_time_passes(start_time: time | None, end_time: time | None) -> bool:
        return start_time is not None and end_time is not None and end_time > start_time

    @classmethod
    def _check_4a_pair(
        cls,
        start: date,
        end: date,
        target: int,
        holidays: Iterable[date],
    ) -> tuple[str, int, str]:
        working_days = cls.networkdays(start, end, holidays) - 1
        if working_days < 0 or working_days <= target:
            return "Yes", working_days, f"NETWORKDAYS-1={working_days} <= target {target}."
        return "No", working_days, f"NETWORKDAYS-1={working_days} > target {target}."

    @classmethod
    def evaluate_4a(
        cls,
        row: dict[str, Any],
        holidays: Iterable[date],
        target_days: int | None,
    ) -> dict[str, Any]:
        eligible, gate_reason = cls._eligible(row)
        if not eligible:
            return {"result": "N/A", "working_days": None, "reason": f"SLA 4A: {gate_reason}", "start_field": None, "end_field": None}
        if target_days is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 4A: kawasan unit belum terdaftar di Master Unit Kawasan.", "start_field": None, "end_field": None}

        schedule = cls._as_date(row.get("tanggal_jadwal_penjemputan"))
        pickup = cls._as_date(row.get("tanggal_penjemputan_dokumen"))
        schedule_time = cls._as_time(row.get("jam_jadwal_penjemputan"))
        pickup_time = cls._as_time(row.get("jam_penjemputan_dokumen"))
        failed = cls._as_date(row.get("tanggal_gagal_penjemputan"))
        failed_time = cls._as_time(row.get("jam_gagal_penjemputan"))
        if schedule is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 4A: Tanggal Jadwal Penjemputan tidak tersedia.", "start_field": "Tanggal Jadwal Penjemputan", "end_field": None}

        if failed is None and failed_time is None:
            end = pickup
            end_field = "Tanggal Penjemputan Dokumen"
            end_time = pickup_time
            if end is None or end_time is None:
                return {"result": "N/A", "working_days": None, "reason": "SLA 4A: Tanggal/Jam Penjemputan Dokumen tidak lengkap.", "start_field": "Tanggal Jadwal Penjemputan", "end_field": end_field}
        elif failed is not None and failed_time is not None:
            if schedule_time is None:
                return {"result": "N/A", "working_days": None, "reason": "SLA 4A: jalur Gagal Penjemputan membutuhkan Tanggal/Jam Jadwal Penjemputan dan Tanggal/Jam Gagal Penjemputan.", "start_field": "Tanggal Jadwal Penjemputan", "end_field": "Tanggal Gagal Penjemputan"}
            end = failed
            end_field = "Tanggal Gagal Penjemputan"
            end_time = failed_time
        else:
            return {"result": "N/A", "working_days": None, "reason": "SLA 4A: Tanggal/Jam Gagal Penjemputan tidak lengkap.", "start_field": "Tanggal Jadwal Penjemputan", "end_field": "Tanggal Gagal Penjemputan"}

        result, working_days, detail = cls._check_4a_pair(schedule, end, target_days, holidays)
        anomaly = None
        if end < schedule:
            anomaly = "Tanggal akhir proses lebih awal daripada Tanggal Jadwal Penjemputan; kondisi ini mengikuti perilaku formula vendor (NETWORKDAYS-1 < 0 => Yes)."
        if result == "Yes":
            return {"result": result, "working_days": working_days, "reason": f"SLA 4A: {detail}", "start_field": "Tanggal Jadwal Penjemputan", "end_field": end_field, "anomaly": anomaly}

        registration = cls._as_date(row.get("tanggal_registrasi"))
        if not cls.period_gate(schedule, registration, holidays):
            return {"result": "N/A", "working_days": working_days, "reason": "SLA 4A: durasi melewati target tetapi Tanggal Jadwal Penjemputan berada di luar period gate vendor.", "start_field": "Tanggal Jadwal Penjemputan", "end_field": end_field, "anomaly": anomaly}

        return {"result": "No", "working_days": working_days, "reason": f"SLA 4A: {detail}", "start_field": "Tanggal Jadwal Penjemputan", "end_field": end_field, "anomaly": anomaly}

    @classmethod
    def _evaluate_4b_path(
        cls,
        path_name: str,
        start_date: date,
        end_date: date,
        start_time: time | None,
        end_time: time | None,
        holidays: Iterable[date],
        cutoff: time,
    ) -> dict[str, Any]:
        if cls._same_day_time_passes(start_time, end_time):
            return {"result": "Yes", "working_days": 0, "reason": f"SLA 4B {path_name}: tanggal sama dan jam akhir lebih besar dari jam awal."}
        wd = cls.networkdays(start_date, end_date, holidays) - 1
        if wd < 0:
            return {"result": "No", "working_days": wd, "reason": f"SLA 4B {path_name}: NETWORKDAYS-1={wd} < 0."}
        if wd <= 2 and end_time is not None and end_time <= cutoff:
            return {"result": "Yes", "working_days": wd, "reason": f"SLA 4B {path_name}: NETWORKDAYS-1={wd} <= 2 dan jam akhir <= {cutoff.strftime('%H:%M')}."}
        reason = f"SLA 4B {path_name}: NETWORKDAYS-1={wd}; batas 2 hari kerja atau cutoff {cutoff.strftime('%H:%M')} tidak terpenuhi."
        return {"result": "No", "working_days": wd, "reason": reason}

    @classmethod
    def evaluate_4b(cls, row: dict[str, Any], holidays: Iterable[date]) -> dict[str, Any]:
        eligible, gate_reason = cls._eligible(row)
        if not eligible:
            return {"result": "N/A", "working_days": None, "reason": f"SLA 4B: {gate_reason}", "start_field": None, "end_field": None}

        schedule = cls._as_date(row.get("tanggal_jadwal_penjemputan"))
        registration = cls._as_date(row.get("tanggal_registrasi"))
        if schedule is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 4B: Tanggal Jadwal Penjemputan tidak tersedia.", "start_field": None, "end_field": None}
        if not cls.period_gate(schedule, registration, holidays):
            return {"result": "N/A", "working_days": None, "reason": "SLA 4B: Tanggal Jadwal Penjemputan berada di luar period gate vendor.", "start_field": None, "end_field": None}

        verification_date = cls._as_date(row.get("tanggal_verifikasi_arsip"))
        verification_time = cls._as_time(row.get("jam_verifikasi_arsip"))
        runner_date = cls._as_date(row.get("tanggal_runner_record_center"))
        runner_time = cls._as_time(row.get("jam_runner_record_center"))
        if verification_date is None or verification_time is None or runner_date is None or runner_time is None:
            return {"result": "N/A", "working_days": None, "reason": "SLA 4B: Tanggal/Jam Verifikasi Arsip atau Runner sampai Record Center tidak lengkap.", "start_field": None, "end_field": None}

        rejection_date = cls._as_date(row.get("tanggal_penolakan_jadwal_penjemputan"))
        rejection_time = cls._as_time(row.get("jam_penolakan_jadwal_penjemputan"))
        reschedule_date = cls._as_date(row.get("tanggal_penjadwalan_inaktif_2"))
        reschedule_time = cls._as_time(row.get("jam_penjadwalan_inaktif_2"))
        pickup_date = cls._as_date(row.get("tanggal_penjemputan_dokumen"))
        pickup_time = cls._as_time(row.get("jam_penjemputan_dokumen"))

        # Exact branch order from vendor formula, translated by header names.
        if rejection_date is not None and rejection_time is not None and reschedule_date is None and pickup_date is None:
            result = cls._evaluate_4b_path(
                "Tanggal Penolakan Jadwal Penjemputan -> Tanggal Runner sampai di Record Center",
                rejection_date,
                runner_date,
                rejection_time,
                runner_time,
                holidays,
                cls.CUTOFF,
            )
            return {**result, "start_field": "Tanggal Penolakan Jadwal Penjemputan", "end_field": "Tanggal Runner sampai di Record Center"}

        if rejection_date is not None and rejection_time is not None and reschedule_date is not None and reschedule_time is not None:
            result = cls._evaluate_4b_path(
                "Tanggal Penolakan Jadwal Penjemputan -> Tanggal Penjadwalan Arsip Inaktif 2",
                rejection_date,
                reschedule_date,
                rejection_time,
                reschedule_time,
                holidays,
                cls.CUTOFF,
            )
            return {**result, "start_field": "Tanggal Penolakan Jadwal Penjemputan", "end_field": "Tanggal Penjadwalan Arsip Inaktif 2"}

        if pickup_date is not None and pickup_time is not None:
            result = cls._evaluate_4b_path(
                "Tanggal Penjemputan Dokumen -> Tanggal Runner sampai di Record Center",
                pickup_date,
                runner_date,
                pickup_time,
                runner_time,
                holidays,
                cls.CUTOFF,
            )
            return {**result, "start_field": "Tanggal Penjemputan Dokumen", "end_field": "Tanggal Runner sampai di Record Center"}

        return {"result": "N/A", "working_days": None, "reason": "SLA 4B: tidak ada jalur tanggal/jam yang lengkap sesuai urutan proses vendor.", "start_field": None, "end_field": None}

    @classmethod
    def evaluate(cls, row: dict[str, Any], holidays: Iterable[date], unit_kawasan: str | None) -> dict[str, Any]:
        target = 1 if unit_kawasan == "Dalam Kawasan" else 2 if unit_kawasan == "Luar Kawasan" else None
        a = cls.evaluate_4a(row, holidays, target)
        b = cls.evaluate_4b(row, holidays)

        if a["result"] == "Yes" or b["result"] == "Yes":
            source = "SLA 4A" if a["result"] == "Yes" else "SLA 4B"
            selected = a if a["result"] == "Yes" else b
            final = "Yes"
        elif a["result"] == "No" or b["result"] == "No":
            source = "FORMULA_NO"
            selected = b if b["result"] == "No" else a
            final = "No"
        else:
            source = "FINAL_NA"
            selected = a
            final = "N/A"

        anomalies: list[str] = []
        if a.get("anomaly"):
            anomalies.append(str(a["anomaly"]))
        if unit_kawasan is None:
            anomalies.append("Unit belum mempunyai mapping kawasan aktif pada Master Unit Kawasan.")

        return {
            "sla4a_result": a["result"],
            "sla4b_result": b["result"],
            "sla4a_working_days": a.get("working_days"),
            "sla4b_working_days": b.get("working_days"),
            "sla4a_start_field": a.get("start_field"),
            "sla4a_end_field": a.get("end_field"),
            "sla4b_start_field": b.get("start_field"),
            "sla4b_end_field": b.get("end_field"),
            "sla4a_reason": a.get("reason"),
            "sla4b_reason": b.get("reason"),
            "sla4_final_result": final,
            "sla4_decision_source": source,
            "sla4_manual_result": "N/A",
            "sla4_reason": f"SLA 4 Final = {final}; SLA 4A={a['result']}; SLA 4B={b['result']}; {selected.get('reason', '')}",
            "sla4_target_days": target,
            "sla4_anomaly": " | ".join(anomalies) if anomalies else None,
        }
