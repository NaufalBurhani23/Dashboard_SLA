from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, ensure_schema
from app.api.routes import router
from app.api.sla4_routes import router as sla4_router

# Import models before create_all so SQLAlchemy registers every table.
from app.models.sla_record import SLARecord  # noqa: F401
from app.models.holiday import HolidayCalendar  # noqa: F401
from app.models.holiday_version import SLA4HolidayVersion  # noqa: F401
from app.models.sla4_record import SLA4Record  # noqa: F401
from app.models.unit_area import UnitArea  # noqa: F401
from app.sla.sla4.unit_area_service import seed_default_units
from app.database import SessionLocal

Base.metadata.create_all(bind=engine)
ensure_schema()

# Seed the vendor reference units only on an empty SLA 4 master table.
with SessionLocal() as _db:
    seed_default_units(_db)

app = FastAPI(title="SLA Monitoring Dashboard — SLA 1 + SLA 2 + SLA 4")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.include_router(sla4_router, prefix="/api")
