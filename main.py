import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from config.sessionsConfig import getOptionalSession
from routers import authRoutes, usersRoutes, lecturasRoutes, adminRoutes


load_dotenv()

app = FastAPI(title="SafeCore IoT")

# Sesiones firmadas para mensajes flash (cookie "session", convive con "safecore_session").
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/public", StaticFiles(directory="public"), name="public")
templates = Jinja2Templates(directory="templates")

# Orden de inclusión: auth (fijas) antes que users (genéricas), lecturas al final.
app.include_router(authRoutes.auth_router)
app.include_router(usersRoutes.users_router)
app.include_router(lecturasRoutes.lecturas_router)
app.include_router(adminRoutes.admin_router)


@app.get("/", include_in_schema=False)
def redirectToHome():
    return RedirectResponse("/home", status_code=303)


@app.get("/home")
async def showHome(request: Request):
    logged = None
    iniciales = None
    sesion = await getOptionalSession(request)
    if sesion is not None:
        from models import usersModel as user_model
        user = user_model.getUserById(sesion.id_usuario)
        if user is not None:
            logged = user["nombre"]
            iniciales = user["nombre"][0] + (user["apellido"][0] if user["apellido"] else "")
    return templates.TemplateResponse(request, "landing.html",
        {"request": request, "logged": logged, "iniciales": iniciales})

