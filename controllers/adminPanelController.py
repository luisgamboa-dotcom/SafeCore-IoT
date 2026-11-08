import urllib.parse
from uuid import UUID

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from config.sessionsConfig import SessionData, cookie as session_cookie, requireAdminUser, requireSuperadminUser
from models import auditoriaModel as audit_model
from models import usersModel as user_model
from utils.commonUtils import adminContext
from utils.flashUtils import popFormFlash

templates = Jinja2Templates(directory="templates")


def showAdminPanel(request: Request,
                   id_sesion: UUID = Depends(session_cookie),
                   sesion: SessionData = Depends(requireAdminUser)):
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/index.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})


def showAuditoria(request: Request,
                  entidad: str = "",
                  registro: str = "",
                  usuario: str = "",
                  desde: str = "",
                  hasta: str = "",
                  pagina: int = 1,
                  id_sesion: UUID = Depends(session_cookie),
                  sesion: SessionData = Depends(requireSuperadminUser)):
    entidades, usuarios = audit_model.getResumenAuditoria()
    filas, total = audit_model.consultarAuditoria(
        entidad=(entidad or None),
        registro_id=(registro or None),
        id_usuario=(usuario or None),
        desde=(desde or None),
        hasta=(hasta or None),
        pagina=pagina,
        por_pagina=30)

    base_qsa = urllib.parse.urlencode(
        {k: v for k, v in [("entidad", entidad), ("registro", registro),
                           ("usuario", usuario), ("desde", desde), ("hasta", hasta)]
         if v}, doseq=True)
    paginas = max(1, -(-total // 30))
    flash_msg, _, flash_ok = popFormFlash(request)
    return templates.TemplateResponse(request, "admin/auditoria.html",
        {"request": request, "flash_msg": flash_msg, "flash_ok": flash_ok,
         "filas": filas, "total": total, "pagina": max(1, int(pagina)),
         "paginas": paginas, "base_qsa": base_qsa,
         "entidades": entidades, "usuarios": usuarios,
         "f_entidad": entidad, "f_registro": registro, "f_usuario": usuario,
         "f_desde": desde, "f_hasta": hasta,
         **adminContext(sesion, user_model.getUserById(sesion.id_usuario))})
