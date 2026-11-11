from fastapi import APIRouter, Depends
from uuid import UUID

import controllers.subscriptionsController as subscriptionsController
from config.sessionsConfig import cookie as session_cookie, verificador

subscriptions_router = APIRouter(tags=["subscriptions"])


# El boton "Mejorar plan" deriva a la pasarela Webpay (aun sin pago real).
subscriptions_router.post("/users/mejorar-plan")(
    subscriptionsController.mejorarPlan)
subscriptions_router.get("/webpay/pago")(
    subscriptionsController.showWebpayPago)
subscriptions_router.post("/users/pago-simulado")(
    subscriptionsController.pagoSimulado)
subscriptions_router.post("/users/bajar-plan")(
    subscriptionsController.bajarPlan)
