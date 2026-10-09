from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.sla_record import SLARecord
from app.api.dashboard_metrics import build_dashboard


def test_dashboard_normalizes_sla1_statuses_and_keeps_sla2_semantics():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()
    try:
        db.add_all([
            SLARecord(
                unit="UNIT A", sla_code="SLA 1", status="ON TIME",
                sla2_final_result="Yes", registration_timestamp=datetime(2026, 8, 3, 9, 0),
                is_denominator=1,
            ),
            SLARecord(
                unit="UNIT A", sla_code="SLA 1", status="OUT OF DATE",
                sla2_final_result="No", registration_timestamp=datetime(2026, 8, 4, 9, 0),
                is_denominator=1,
            ),
            SLARecord(
                unit="UNIT B", sla_code="SLA 1", status="INCOMPLETE",
                sla2_final_result="N/A", registration_timestamp=datetime(2026, 8, 5, 9, 0),
                is_denominator=1,
            ),
        ])
        db.commit()

        payload = build_dashboard(db, sla="ALL")
        s1 = payload["summaries"]["SLA 1"]
        s2 = payload["summaries"]["SLA 2"]

        assert s1["total_records"] == 3
        assert s1["on_time"] == 1
        assert s1["out_of_date"] == 1
        assert s1["incomplete"] == 1
        assert s1["percentage"] == 33.33

        assert s2["total_records"] == 3
        assert s2["on_time"] == 1
        assert s2["out_of_date"] == 1
        assert s2["incomplete"] == 1
        assert s2["percentage"] == 33.33
    finally:
        db.close()
