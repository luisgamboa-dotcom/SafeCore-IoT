"""Barrido periodico de alertas y estado de dispositivos (hilo daemon).

Cada intervalo evalua las reglas de las zonas con dispositivos activos (para
abrir/resolver alertas y generar sus notificaciones) y marca como offline los
equipos sin comunicacion reciente. Complementa la evaluacion que dispara la
ingesta (utils/batchStore), cubriendo cambios de vigencia de las reglas y
equipos que dejan de enviar.

Se inicia junto a la app (main.py). Se desactiva con SAFECORE_ALERTS=0 y el
intervalo se ajusta con SAFECORE_ALERTS_INTERVAL (segundos, minimo 15).
"""
import os
import threading
import time

from models import devicesModel as dev_model
from models import rulesModel as rule_model

def _intervalo_env():
    try:
        return max(15, int(os.getenv("SAFECORE_ALERTS_INTERVAL") or 60))
    except (TypeError, ValueError):
        return 60


_INTERVALO = _intervalo_env()
_ACTIVADO = os.getenv("SAFECORE_ALERTS") != "0"

_hilo = None


def _bucle():
    while True:
        time.sleep(_INTERVALO)
        try:
            dev_model.markTimedOutDevices()
        except Exception:
            pass
        try:
            for id_zona in rule_model.getZonasConDispositivosActivos():
                rule_model.evaluateZone(id_zona)
        except Exception:
            pass


def iniciar_barrido():
    """Arranca el hilo daemon del barrido (idempotente)."""
    global _hilo
    if not _ACTIVADO:
        print("[alertas] desactivado por SAFECORE_ALERTS=0")
        return
    if _hilo is not None:
        return
    _hilo = threading.Thread(target=_bucle, name="safecore-alertas", daemon=True)
    _hilo.start()
    print(f"[alertas] barrido activo cada {_INTERVALO}s")
