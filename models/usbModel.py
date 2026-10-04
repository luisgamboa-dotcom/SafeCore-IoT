# models/usbModel.py — lectura USB en vivo SIN guardar en la base de datos.
# Un hilo lector vuelca las líneas del puerto serie a un buffer en memoria
# (collections.deque). Nada se inserta en MySQL: es solo testeo visual.
import threading
import time
from collections import deque

import serial
from serial.tools import list_ports

_lines = deque(maxlen=200)  # cada item: {"t": "HH:MM:SS", "raw": "..."}
_lock = threading.Lock()
_ser = None
_port = None
_baud = None
_error = None
_generation = 0


def listUsbPorts():
    return [{"device": p.device, "description": p.description or ""}
            for p in list_ports.comports()]


def _readLoop(gen):
    global _error
    while True:
        with _lock:
            if gen != _generation or _ser is None:
                return
            ser = _ser
        try:
            raw = ser.readline()
        except Exception as e:
            with _lock:
                _error = f"Error leyendo el puerto: {e}"
            return
        if raw:
            texto = raw.decode("utf-8", errors="replace").strip()
            if texto:
                _lines.append({"t": time.strftime("%H:%M:%S"), "raw": texto})


def openUsbPort(port, baud):
    """Abre el puerto y arranca el hilo lector. Retorna (True, None) o (False, mensaje)."""
    global _ser, _port, _baud, _error, _generation
    with _lock:
        if _ser is not None and _ser.is_open and _port == port and _baud == baud:
            return True, None
        if _ser is not None:
            try:
                _ser.close()
            except Exception:
                pass
            _ser = None
        _generation += 1
        _error = None
        try:
            _ser = serial.Serial(port, int(baud), timeout=1)
        except serial.SerialException as e:
            _ser = None
            texto = str(e)
            if "busy" in texto or "16" in texto:
                return False, "Puerto ocupado por otro programa (cierra el Monitor Serie de Arduino)."
            return False, f"No se pudo abrir el puerto: {texto}"
        _port, _baud = port, int(baud)
        gen = _generation
    hilo = threading.Thread(target=_readLoop, args=(gen,), daemon=True)
    hilo.start()
    return True, None


def closeUsbPort():
    global _ser, _error, _generation
    with _lock:
        _generation += 1
        if _ser is not None:
            try:
                _ser.close()
            except Exception:
                pass
            _ser = None
        _error = None


def getUsbStatus():
    with _lock:
        conectado = _ser is not None and _ser.is_open
        return {"connected": conectado, "port": _port, "baud": _baud,
                "buffered": len(_lines), "error": _error}


def getLiveLines(limit=50):
    limit = max(1, min(int(limit), 200))
    with _lock:
        return list(_lines)[-limit:]
