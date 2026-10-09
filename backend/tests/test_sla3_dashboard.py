from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.sla_record import SLARecord
from app.api.dashboard_metrics import build_dashboard


def test_sla3_dashboard_summary_and_unit_rows():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add_all([
            SLARecord(
                unit='Kantor Pusat', registration_timestamp=datetime(2026, 8, 3),
                sla_code='SLA 1', status='INCOMPLETE', is_denominator=1,
                sla3a_result='Yes', sla3b_result='N/A', sla3_final_result='Yes',
            ),
            SLARecord(
                unit='UID JABAR', registration_timestamp=datetime(2026, 8, 4),
                sla_code='SLA 1', status='INCOMPLETE', is_denominator=1,
                sla3a_result='No', sla3b_result='N/A', sla3_final_result='No',
            ),
            SLARecord(
                unit='UID JABAR', registration_timestamp=datetime(2026, 8, 5),
                sla_code='SLA 1', status='INCOMPLETE', is_denominator=1,
                sla3a_result='N/A', sla3b_result='N/A', sla3_final_result='N/A',
            ),
        ])
        db.commit()

        payload = build_dashboard(db, sla='SLA 3')
        s3 = payload['summaries']['SLA 3']
        assert s3['total_records'] == 3
        assert s3['on_time'] == 1
        assert s3['out_of_date'] == 1
        assert s3['incomplete'] == 1
        assert s3['denominator'] == 3
        assert s3['percentage'] == 33.33

        rows = {row['unit']: row for row in payload['unit_table']}
        assert rows['Kantor Pusat']['on_time'] == 1
        assert rows['Kantor Pusat']['denominator'] == 1
        assert rows['UID JABAR']['on_time'] == 0
        assert rows['UID JABAR']['denominator'] == 2
        assert rows['UID JABAR']['percentage'] == 0.0

        all_payload = build_dashboard(db, sla='ALL')
        all_row = {row['unit']: row for row in all_payload['unit_table']}['UID JABAR']
        assert 'sla3' in all_row
        assert all_row['sla3']['denominator'] == 2
    finally:
        db.close()
