import os
from dotenv import load_dotenv


load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from utils import alertScheduler, discovery
from routers import (authRoutes, homeRoutes, readingRoutes, deviceRoutes,
                     adminPanelRoutes, userRoutes, organizationRoutes,
                     installationRoutes, zoneRoutes, myOrganizationRoutes,
                     ruleRoutes, notificationsRoutes, subscriptionRoutes,
                     contactRoutes)


discovery.iniciar_descubrimiento()
alertScheduler.iniciar_barrido()

app = FastAPI(title="SafeCore IoT")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/public", StaticFiles(directory="public"), name="public")

app.include_router(homeRoutes.home_router)
app.include_router(authRoutes.auth_router)
app.include_router(readingRoutes.readings_router)
app.include_router(deviceRoutes.devices_router)
app.include_router(adminPanelRoutes.admin_router)
app.include_router(userRoutes.admin_router)
app.include_router(organizationRoutes.admin_router)
app.include_router(installationRoutes.admin_router)
app.include_router(zoneRoutes.admin_router)
app.include_router(myOrganizationRoutes.my_org_router)
app.include_router(ruleRoutes.rules_router)
app.include_router(notificationsRoutes.notifications_router)
app.include_router(subscriptionRoutes.subscriptions_router)
app.include_router(contactRoutes.contact_router)
