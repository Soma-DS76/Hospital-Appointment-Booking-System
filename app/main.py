from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers.auth import router as auth_router
from app.routers.departments import router as departments_router
from app.routers.doctors import router as doctors_router
from app.routers.schedules import router as schedules_router
from app.routers.appointments import router as appointments_router
from app.routers.consultations import router as consultations_router
from app.routers.files import router as files_router
from app.routers.health import router as health_router
from app.routers.websockets import router as websockets_router
from app.routers.reports import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI( title="Hospital Appointment Booking System",
    version="1.0.0",
    description="FastAPI backend for hospital appointment management",
    lifespan=lifespan )

app.add_middleware( CORSMiddleware, allow_origins=["*"], allow_credentials=True, 
                    allow_methods=["*"], allow_headers=["*"] )

app.include_router(auth_router)
app.include_router(departments_router)
app.include_router(doctors_router)
app.include_router(schedules_router)
app.include_router(appointments_router)
app.include_router(consultations_router)
app.include_router(files_router)
app.include_router(health_router)
app.include_router(websockets_router)
app.include_router(reports_router)


@app.get("/")
async def root():
    return {"message": "Hospital Appointment Booking System API is running"}


