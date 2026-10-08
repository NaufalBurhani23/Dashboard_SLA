from typing import Any, Dict

from app.sla.sla2.calculator import SLA2Calculator as _Base  # _norm, _as_date, _as_time, _period_gate_2a

# Pola manual SLA 3 yang di-ACC, dicocokkan lewat Sumber + Status Registrasi + Posisi Data.
# Status Inisiasi sengaja tidak dipakai (nilainya bervariasi pada status yang sama).
# "Ditolak Command Center" sengaja TIDAK ada: vendor menandai N/A, bukan Yes.
SLA3_MANUAL_RULES = (
    ("SLA3-MAN-01", "registrasi masuk", "command center",
     "Registrasi Masuk masih tertahan di Command Center."),
    ("SLA3-MAN-02", "registrasi masuk lanjutan", "command center",
     "Registrasi Masuk Lanjutan masih tertahan di Command Center."),
    ("SLA3-MAN-03", "pickup failed", "",
     "Pickup Failed: gagal jemput di lapangan, di luar kendali penjadwalan."),
)


def apply_sla3_manual_check(row: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    miss = {"result": "N/A", "rule_code": None, "reason": "Tidak ada pola manual SLA 3 yang cocok."}
    n = _Base._norm
    if n(row.get("sumber")) != "elarch":
        return miss

    # Gate prasyarat sama dengan SLA 3A/3B.
    if n(row.get("format_arsip")) != "fisik":
        return miss
    doc = n(row.get("document_type"))
    x = _Base._as_date(row.get("tanggal_penjadwalan_inaktif"))
    y = _Base._as_time(row.get("jam_penjadwalan_inaktif"))
    if not (doc == "inaktif" or (doc == "aktif" and x is not None and y is not None)):
        return miss

    p = _Base._as_date(row.get("tanggal_registrasi"))
    if p is None or not _Base._period_gate_2a(p, context):
        return miss

    status, posisi = n(row.get("status_registrasi")), n(row.get("posisi_data"))
    for code, rule_status, rule_posisi, reason in SLA3_MANUAL_RULES:
        if status == rule_status and posisi == rule_posisi:
            return {"result": "Yes", "rule_code": code, "reason": reason}
    return miss