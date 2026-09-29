import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from routers import routes

load_dotenv()

app = FastAPI(title="CRUD FastAPI + Jinja2")
# Sesiones firmadas para mensajes flash (cookie "session", convive con "safecore_session").
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(routes.users_router)
app.include_router(routes.datos_router)

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "landing.html", {"request": request})