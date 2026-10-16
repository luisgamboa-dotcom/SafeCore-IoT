"""Rutas de lecturas y datos (ingesta del dispositivo + vistas)."""
from fastapi import APIRouter

import controllers.lecturasController as lecturasController

lecturas_router = APIRouter(tags=["ingest", "datos"])


lecturas_router.post("/api/ingest")(lecturasController.ingestReadings)
lecturas_router.get("/api/live")(lecturasController.getLiveReadings)
lecturas_router.get("/api/ultimas")(lecturasController.getLatestReadings)
lecturas_router.get("/datos")(lecturasController.showDataPage)
lecturas_router.get("/dashboard")(lecturasController.showDataPage)
lecturas_router.get("/dashboard/dispositivos/{id_dispositivo}")(lecturasController.showDeviceDetail)
