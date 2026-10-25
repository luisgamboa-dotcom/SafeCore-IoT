"""Ultima IP conocida de cada nodo IoT, por codigo_serial.

Se persiste en data/nodo_ips.json (fichero, sin tocar el esquema de la BD)
para que el panel /admin/devices muestre siempre donde esta el nodo y se
pueda abrir su pagina de configuracion (PWA http://<ip>/) aunque cambie de
red. Escritura limitada: solo al cambiar de IP o como maximo 1 vez por
minuto por nodo.
"""
import json
import os
import threading
import time

_PATH = os.path.join("data", "nodo_ips.json")
_LOCK = threading.Lock()

_registros = {}          # {serial: {"ip": ..., "ts": float, "escrito_ts": float}}
_cargado = False


def _cargar():
    global _cargado
    if not _cargado:
        _cargado = True
        try:
            with open(_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                _registros.update(raw)
        except FileNotFoundError:
            pass
        except Exception:
            pass  # fichero corrupto: arrancamos de cero


def _guardar():
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        salida = {s: {"ip": r["ip"], "ts": r["ts"]}
                  for s, r in _registros.items() if "ip" in r}
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(salida, f, indent=2)
    except Exception:
        pass  # nunca bloquear el ingest por el fichero


def recordar(serial: str, ip: str):
    """Anota la IP del nodo si cambio o como maximo 1 vez por minuto."""
    if not serial or not ip:
        return
    with _LOCK:
        _cargar()
        reg = _registros.get(serial) or {}
        ahora = time.time()
        cambio = reg.get("ip") != ip
        if not cambio and ahora - reg.get("escrito_ts", 0) < 60:
            return
        _registros[serial] = {"ip": ip, "ts": ahora, "escrito_ts": ahora}
        _guardar()


def obtener(serial: str):
    """Devuelve {"ip": ..., "ts": ...} o None si no hay registro."""
    with _LOCK:
        _cargar()
        reg = _registros.get(serial)
        if reg and "ip" in reg:
            return {"ip": reg["ip"], "ts": reg["ts"]}
        return None
