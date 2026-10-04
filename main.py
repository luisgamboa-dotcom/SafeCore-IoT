import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from routers import authRoutes, usersRoutes, lecturasRoutes

load_dotenv()

app = FastAPI(title="CRUD FastAPI + Jinja2")
# Sesiones firmadas para mensajes flash (cookie "session", convive con "safecore_session").
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")
templates = Jinja2Templates(directory="templates")

# Orden de inclusión: auth (fijas) antes que users (genéricas), lecturas al final.
app.include_router(authRoutes.auth_router)
app.include_router(usersRoutes.users_router)
app.include_router(lecturasRoutes.lecturas_router)

@app.get("/", include_in_schema=False)
def redirectToHome():
    return RedirectResponse("/home", status_code=303)


@app.get("/home")
def showHome(request: Request):
    return templates.TemplateResponse(request, "landing.html", {"request": request})
