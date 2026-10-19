"""Readings routes: device ingest and live/data dashboard."""
from fastapi import APIRouter

import controllers.readingsController as readingsController

readings_router = APIRouter(tags=["ingest", "data"])


readings_router.post("/api/ingest")(readingsController.ingestReadings)
readings_router.get("/api/live")(readingsController.getLiveReadings)
readings_router.get("/api/ultimas")(readingsController.getLatestReadings)
readings_router.get("/datos")(readingsController.showDataPage)
readings_router.get("/dashboard")(readingsController.showDataPage)
