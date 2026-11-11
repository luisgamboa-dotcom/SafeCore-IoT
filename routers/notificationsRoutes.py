from fastapi import APIRouter, Depends
from uuid import UUID

import controllers.notificationsController as notificationsController
from config.sessionsConfig import SessionData, cookie as session_cookie, verificador
from models import notificationsModel as notif_model

notifications_router = APIRouter(tags=["notifications"])


notifications_router.get("/dashboard/notificaciones")(notificationsController.showNotificacionesPage)
notifications_router.post("/dashboard/notificaciones/{id_notificacion}/leer")(notificationsController.marcarLeidaNotificacion)


notifications_router.get("/dashboard/notificaciones/configurar")(notificationsController.showConfigCanales)
notifications_router.post("/dashboard/notificaciones/configurar")(notificationsController.saveConfigCanales)


def contarNoLeidas(id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(verificador)):
    # Plan gratuito: campana inactiva (Funcion Premium).
    try:
        from utils.commonUtils import esOrganizacionPremium
        if not esOrganizacionPremium(sesion):
            return {"ok": True, "no_leidas": 0}
    except Exception:
        pass
    try:
        no_leidas = notif_model.countNoLeidas(sesion.id_usuario)
    except Exception:
        no_leidas = 0
    return {"ok": True, "no_leidas": no_leidas}


notifications_router.get("/api/notificaciones/no-leidas")(contarNoLeidas)
