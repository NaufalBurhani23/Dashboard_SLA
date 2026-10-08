from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.database import Base


class SLA4HolidayVersion(Base):
    """Version registry so an empty calendar can still have a latest version."""

    __tablename__ = "sla4_holiday_versions"
    __table_args__ = (UniqueConstraint("year", "version", name="uq_sla4_holiday_version"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    version = Column(String(80), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
