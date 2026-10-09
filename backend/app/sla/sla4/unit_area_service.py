from __future__ import annotations

from datetime import date
import re

from sqlalchemy.orm import Session

from app.models.unit_area import UnitArea


DEFAULT_VENDOR_UNITS = [
    ("Kantor Pusat", "Pusat", "Luar Kawasan"),
    ("PUSDIKLAT", "Pendukung", "Dalam Kawasan"),
    ("PUSERTIF", "Pendukung", "Luar Kawasan"),
    ("PUSHARLIS", "Pendukung", "Dalam Kawasan"),
    ("PUSLITBANG", "Pendukung", "Dalam Kawasan"),
    ("PUSMANPRO", "Pendukung", "Dalam Kawasan"),
    ("UID Bali", "Pendukung", "Dalam Kawasan"),
    ("UID Banten", "Pendukung", "Luar Kawasan"),
    ("UID JABAR", "Pendukung", "Dalam Kawasan"),
    ("UID JATENG", "Pendukung", "Luar Kawasan"),
    ("UID JATIM", "Pendukung", "Dalam Kawasan"),
    ("UID JAYA", "Pendukung", "Luar Kawasan"),
    ("UIK SBS", "Pendukung", "Dalam Kawasan"),
    ("UIK SBU", "Pendukung", "Dalam Kawasan"),
    ("UIK TJB", "Pendukung", "Dalam Kawasan"),
    ("UIP JBB", "Pendukung", "Dalam Kawasan"),
    ("UIP JBT", "Pendukung", "Luar Kawasan"),
    ("UIP JBTB", "Pendukung", "Dalam Kawasan"),
    ("UIP2B JAMALI", "Pendukung", "Dalam Kawasan"),
    ("UIT JBB", "Pendukung", "Dalam Kawasan"),
    ("UIT JBT", "Pendukung", "Luar Kawasan"),
    ("UIT JBTB", "Pendukung", "Dalam Kawasan"),
]


def normalize_unit(value: str | None) -> str:
    value = (value or "").strip().upper()
    return re.sub(r"\s+", " ", value)


def target_days(kawasan: str | None) -> int | None:
    return 1 if kawasan == "Dalam Kawasan" else 2 if kawasan == "Luar Kawasan" else None


def find_unit(db: Session, unit_name: str | None, on_date: date | None = None) -> UnitArea | None:
    normalized = normalize_unit(unit_name)
    if not normalized:
        return None
    q = db.query(UnitArea).filter(
        UnitArea.unit_name_normalized == normalized,
        UnitArea.active.is_(True),
    )
    if on_date:
        q = q.filter(
            (UnitArea.valid_from.is_(None) | (UnitArea.valid_from <= on_date)),
            (UnitArea.valid_to.is_(None) | (UnitArea.valid_to >= on_date)),
        )
    return q.order_by(UnitArea.valid_from.desc().nullslast(), UnitArea.id.desc()).first()


def seed_default_units(db: Session) -> int:
    if db.query(UnitArea).count() > 0:
        return 0
    for name, unit_type, kawasan in DEFAULT_VENDOR_UNITS:
        db.add(
            UnitArea(
                unit_name=name,
                unit_name_normalized=normalize_unit(name),
                unit_type=unit_type,
                kawasan=kawasan,
                active=True,
            )
        )
    db.commit()
    return len(DEFAULT_VENDOR_UNITS)
