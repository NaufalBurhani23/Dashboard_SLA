from sqlalchemy import Column, Integer, String, Date
from app.database import Base


class HolidayCalendar(Base):
    __tablename__ = "holiday_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    holiday_date = Column(Date, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    version = Column(String(80), nullable=False, index=True)
