"""
    Rutas de lecturas y datos (ingesta del dispositivo + vistas).
    Delegan en controllers/lecturasController.py.
"""

# routers/lecturasRoutes.py
from fastapi import APIRouter

import controllers.lecturasController as lecturasController

lecturas_router = APIRouter(tags=["ingest", "datos"])


lecturas_router.post("/api/ingest")(lecturasController.ingestReadings)
lecturas_router.get("/api/ultimas")(lecturasController.getLatestReadings)
lecturas_router.get("/datos")(lecturasController.showDataPage)
