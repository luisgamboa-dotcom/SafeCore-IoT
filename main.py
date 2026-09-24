import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import users

load_dotenv()

app = FastAPI(title="CRUD FastAPI + Jinja2")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
def root():
    return RedirectResponse("/users", status_code=303)