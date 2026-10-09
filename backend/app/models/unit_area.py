from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, UniqueConstraint

from app.database import Base


class UnitArea(Base):
    """Master unit -> Pusat/Pendukung + Dalam/Luar Kawasan for SLA 4."""

    __tablename__ = "sla4_unit_area"
    __table_args__ = (
        UniqueConstraint(
            "unit_name_normalized",
            "valid_from",
            name="uq_sla4_unit_area_name_start",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_name = Column(String(255), nullable=False, index=True)
    unit_name_normalized = Column(String(255), nullable=False, index=True)
    unit_type = Column(String(30), nullable=False, default="Pendukung")
    kawasan = Column(String(30), nullable=False, default="Dalam Kawasan")
    active = Column(Boolean, nullable=False, default=True, index=True)
    valid_from = Column(Date, nullable=True, index=True)
    valid_to = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
