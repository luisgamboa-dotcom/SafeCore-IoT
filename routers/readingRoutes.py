"""Rutas de lecturas: ingesta de dispositivos y panel de datos en vivo."""
from fastapi import APIRouter

import controllers.readingsController as readingsController

readings_router = APIRouter(tags=["ingest", "data"])


readings_router.post("/api/ingest")(readingsController.ingestReadings)
readings_router.get("/api/live")(readingsController.getLiveReadings)
readings_router.get("/api/ultimas")(readingsController.getLatestReadings)
readings_router.get("/api/historico")(readingsController.getHistoricoReadings)
readings_router.get("/api/zonas/{id_zona}/series")(readingsController.getZonaSeries)
readings_router.get("/api/buffer")(readingsController.getBatchView)
readings_router.get("/datos")(readingsController.showDataPage)
readings_router.get("/dashboard")(readingsController.showDataPage)
readings_router.get("/datos/live")(readingsController.showLiveView)
readings_router.get("/dashboard/live")(readingsController.showLiveView)
readings_router.get("/api/nodes/{serial}/config")(readingsController.nodeConfig)
