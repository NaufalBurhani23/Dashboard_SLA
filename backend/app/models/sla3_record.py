from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from app.database import Base


class SLA3Record(Base):
    __tablename__ = "sla3_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_file_name = Column(String(255), nullable=True)
    reporting_period = Column(String(20), nullable=True, index=True)
    nomor_registrasi = Column(String(255), nullable=True, index=True)
    nama_dokumen = Column(Text, nullable=True)
    unit = Column(String(255), nullable=True, index=True)
    unit_type = Column(String(30), nullable=True)
    kawasan = Column(String(30), nullable=True)
    sumber = Column(String(100), nullable=True)
    status_registrasi = Column(String(500), nullable=True)
    status_inisiasi = Column(String(255), nullable=True)
    posisi_data = Column(String(255), nullable=True)
    format_arsip = Column(String(100), nullable=True)
    document_type = Column(String(100), nullable=True)

    tanggal_registrasi = Column(Date, nullable=True)
    jam_registrasi = Column(String(30), nullable=True)
    tanggal_penjadwalan_inaktif = Column(Date, nullable=True)
    jam_penjadwalan_inaktif = Column(String(30), nullable=True)
    tanggal_jadwal_penjemputan = Column(Date, nullable=True)
    jam_jadwal_penjemputan = Column(String(30), nullable=True)
    tanggal_penjadwalan_inaktif_2 = Column(Date, nullable=True)
    jam_penjadwalan_inaktif_2 = Column(String(30), nullable=True)

    sla3a_result = Column(String(10), nullable=False, default="N/A")
    sla3a_working_days = Column(Integer, nullable=True)
    sla3b_result = Column(String(10), nullable=False, default="N/A")
    sla3b_working_days = Column(Integer, nullable=True)

    sla3_final_result = Column(String(10), nullable=False, default="N/A", index=True)
    sla3_decision_source = Column(String(80), nullable=True)
    sla3_manual_result = Column(String(10), nullable=True, default="N/A")
    sla3_reason = Column(Text, nullable=True)
    sla3_target_days = Column(Integer, nullable=True)

    holiday_calendar_versions = Column(Text, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)