"""app/api/v1/__init__.py — V1 API router aggregator."""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.contacts import router as contacts_router
from app.api.v1.responders import router as responders_router
from app.api.v1.zones import router as zones_router
from app.api.v1.weather import router as weather_router
from app.api.v1.news import router as news_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.risk import router as risk_router
from app.api.v1.gps import router as gps_router
from app.api.v1.detection import router as detection_router
from app.api.v1.sos import router as sos_router
from app.api.v1.communication import router as communication_router
from app.api.v1.mesh import router as mesh_router
from app.api.v1.blockchain import router as blockchain_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.field_tests import router as field_tests_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.audit import router as audit_router

router = APIRouter()

router.include_router(auth_router,          prefix="/auth",         tags=["Authentication"])
router.include_router(users_router,         prefix="/users",        tags=["Users"])
router.include_router(contacts_router,      prefix="/contacts",     tags=["Emergency Contacts"])
router.include_router(responders_router,    prefix="/responders",   tags=["Responders"])
router.include_router(zones_router,         prefix="/zones",        tags=["Geographic Zones"])
router.include_router(weather_router,       prefix="/weather",      tags=["Weather"])
router.include_router(news_router,          prefix="/news",         tags=["News Intelligence"])
router.include_router(incidents_router,     prefix="/incidents",    tags=["Incidents"])
router.include_router(risk_router,          prefix="/risk",         tags=["Risk Engine"])
router.include_router(gps_router,           prefix="/gps",          tags=["GPS Safety"])
router.include_router(detection_router,     prefix="/detection",    tags=["Audio Detection"])
router.include_router(sos_router,           prefix="/sos",          tags=["SOS & Emergency"])
router.include_router(communication_router, prefix="/communication",tags=["Communication"])
router.include_router(mesh_router,          prefix="/mesh",         tags=["Mesh Network"])
router.include_router(blockchain_router,    prefix="/blockchain",   tags=["Blockchain Identity"])
router.include_router(telemetry_router,     prefix="/telemetry",    tags=["Mobile Telemetry"])
router.include_router(field_tests_router,   prefix="/field-tests",  tags=["Field Tests"])
router.include_router(experiments_router,   prefix="/experiments",  tags=["Research Experiments"])
router.include_router(audit_router,         prefix="/audit",        tags=["Audit Logs"])
