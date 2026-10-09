from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.holiday import HolidayCalendar
from app.models.holiday_version import SLA4HolidayVersion


def _version_number(version: str | None) -> int:
    if not version:
        return 0
    try:
        return int(str(version).rsplit("-v", 1)[1])
    except Exception:
        return 0


def _ensure_version_registry(db: Session, year: int) -> None:
    exists = db.query(SLA4HolidayVersion).filter(SLA4HolidayVersion.year == year).first()
    if exists:
        return
    versions = [row[0] for row in db.query(HolidayCalendar.version).filter(HolidayCalendar.year == year).all()]
    if versions:
        db.add(SLA4HolidayVersion(year=year, version=max(versions, key=_version_number)))
        db.flush()


def latest_version(db: Session, year: int) -> Optional[str]:
    _ensure_version_registry(db, year)
    rows = db.query(SLA4HolidayVersion.version).filter(SLA4HolidayVersion.year == year).all()
    versions = [row[0] for row in rows]
    if versions:
        return max(versions, key=_version_number)
    # Fall back to the legacy holiday table if version registry has not been seeded yet.
    versions = [row[0] for row in db.query(HolidayCalendar.version).filter(HolidayCalendar.year == year).all()]
    return max(versions, key=_version_number) if versions else None


def next_version(db: Session, year: int) -> str:
    current = latest_version(db, year)
    return f"HC-{year}-v{_version_number(current) + 1}"


def _rows_for_version(db: Session, year: int, version: str | None):
    if not version:
        return []
    return (
        db.query(HolidayCalendar)
        .filter(HolidayCalendar.year == year, HolidayCalendar.version == version)
        .order_by(HolidayCalendar.holiday_date, HolidayCalendar.id)
        .all()
    )


def active_rows(db: Session, year: int):
    return _rows_for_version(db, year, latest_version(db, year))


def active_holidays(db: Session, year: int) -> list[date]:
    return [row.holiday_date for row in active_rows(db, year)]


def holidays_for_range(db: Session, start_date: date, end_date: date) -> tuple[list[date], dict[str, str]]:
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    values: set[date] = set()
    versions: dict[str, str] = {}
    for year in range(start_date.year, end_date.year + 1):
        version = latest_version(db, year)
        if version:
            versions[str(year)] = version
            values.update(active_holidays(db, year))
    return sorted(values), versions


def _snapshot(db: Session, year: int) -> list[tuple[date, str]]:
    return [(row.holiday_date, row.description or "") for row in active_rows(db, year)]


def write_version(db: Session, year: int, rows: Iterable[tuple[date, str]]) -> str:
    version = next_version(db, year)
    db.add(SLA4HolidayVersion(year=year, version=version))
    for holiday_date, description in sorted(set(rows)):
        db.add(
            HolidayCalendar(
                year=year,
                holiday_date=holiday_date,
                description=description or "",
                version=version,
            )
        )
    db.flush()
    return version


def add_holiday(db: Session, holiday_date: date, description: str = "") -> str:
    rows = _snapshot(db, holiday_date.year)
    if any(d == holiday_date for d, _ in rows):
        raise ValueError("Tanggal tersebut sudah ada di kalender aktif.")
    rows.append((holiday_date, description))
    return write_version(db, holiday_date.year, rows)


def edit_holiday(db: Session, holiday_id: int, new_date: date, description: str = "") -> str:
    row = db.query(HolidayCalendar).filter(HolidayCalendar.id == holiday_id).first()
    if not row:
        raise ValueError("Hari libur tidak ditemukan.")
    year = row.year
    current_version = latest_version(db, year)
    if row.version != current_version:
        raise ValueError("Record kalender yang dipilih bukan bagian dari versi aktif. Muat ulang kalender terbaru.")
    if new_date.year != year:
        raise ValueError("Edit tanggal tidak boleh memindahkan hari libur ke tahun lain; hapus lalu tambah pada tahun baru.")
    rows = [(d, desc) for d, desc in _snapshot(db, year) if d != row.holiday_date]
    if any(d == new_date for d, _ in rows):
        raise ValueError("Tanggal tujuan sudah ada di kalender aktif.")
    rows.append((new_date, description))
    return write_version(db, year, rows)


def delete_holiday(db: Session, holiday_id: int) -> str:
    row = db.query(HolidayCalendar).filter(HolidayCalendar.id == holiday_id).first()
    if not row:
        raise ValueError("Hari libur tidak ditemukan.")
    year = row.year
    current_version = latest_version(db, year)
    if row.version != current_version:
        raise ValueError("Record kalender yang dipilih bukan bagian dari versi aktif. Muat ulang kalender terbaru.")
    rows = [(d, desc) for d, desc in _snapshot(db, year) if d != row.holiday_date]
    return write_version(db, year, rows)
