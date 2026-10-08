from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lightweight SQLite migration for adding SLA 2 columns to existing 1 Oktober DB.
def ensure_schema():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "sla_records" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("sla_records")}
    additions = {
        "tanggal_penolakan_jadwal_penjemputan_raw": "VARCHAR(80)",
        "jam_penolakan_jadwal_penjemputan_raw": "VARCHAR(80)",
        "tanggal_gagal_penjemputan_raw": "VARCHAR(80)",
        "jam_gagal_penjemputan_raw": "VARCHAR(80)",
        "tanggal_jadwal_penjemputan_raw": "VARCHAR(80)",
        "jam_jadwal_penjemputan_raw": "VARCHAR(80)",
        "tanggal_penjemputan_dokumen_raw": "VARCHAR(80)",
        "jam_penjemputan_dokumen_raw": "VARCHAR(80)",
        "tanggal_penjadwalan_inaktif_2_raw": "VARCHAR(80)",
        "jam_penjadwalan_inaktif_2_raw": "VARCHAR(80)",
        "sla2a_result": "VARCHAR(10)",
        "sla2b_result": "VARCHAR(10)",
        "sla2_final_result": "VARCHAR(10)",
        "sla2_manual_result": "VARCHAR(10)",
        "sla2_decision_source": "VARCHAR(80)",
        "sla2_manual_rule": "VARCHAR(120)",
        "sla2_working_days": "INTEGER",
        "sla2a_working_days": "INTEGER",
        "sla2b_working_days": "INTEGER",
        "sla2_flow_stage": "VARCHAR(80)",
        "sla2_reason": "TEXT",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE sla_records ADD COLUMN {name} {ddl}"))
