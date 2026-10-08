from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, ensure_schema
from app.api.routes import router
from app.models.sla_record import SLARecord
from app.models.holiday import HolidayCalendar

Base.metadata.create_all(bind=engine)
ensure_schema()

app = FastAPI(title="SLA Monitoring Dashboard — SLA 1 + SLA 2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")
