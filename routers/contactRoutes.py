from fastapi import APIRouter, Depends

import controllers.contactController as contactController
from config.sessionsConfig import getOptionalSession

contact_router = APIRouter(tags=["contact"])

# Pagina publica: accesible sin iniciar sesion.
contact_router.get("/contacto")(
    contactController.showContacto)
contact_router.post("/contacto")(
    contactController.enviarContacto)
