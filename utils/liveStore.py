"""Buffer en vivo (solo memoria): la ingesta NO se guarda en disco/DB.

Requisito del proyecto: visualizacion en tiempo real sin persistencia.
El dispositivo tampoco guarda: si el POST falla, descarta y sigue sensando.
"""
import threading
import time
from collections import deque
from typing import Any, Dict, List

_MAX = 200
_lock = threading.Lock()
_buf: deque = deque(maxlen=_MAX)
_last_seen: Dict[str, Any] = {}


def push(device_serial: str, fw: str | None, seq: int,
         readings: List[Dict[str, Any]]) -> Dict[str, Any]:
    ts = time.time()
    items = []
    with _lock:
        for r in readings:
            item = {
                "codigo_serial": device_serial,
                "dispositivo": device_serial,
                "magnitud": r["tipo"],
                "valor": r["valor_crudo"],
                "calidad": r["calidad"],
                "fecha_hora": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                "seq": seq,
                "fw": fw,
                "_ts": ts,
            }
            _buf.appendleft(item)
            items.append(item)
        _last_seen[device_serial] = {"seq": seq, "ts": ts, "fw": fw}
    return {"recibidas": len(items), "ts": ts}


def get_latest(limit: int = 50) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), _MAX))
    with _lock:
        out = list(_buf)[:limit]
    # Sin claves internas.
    return [{k: v for k, v in d.items() if not k.startswith("_")} for d in out]


def status() -> Dict[str, Any]:
    with _lock:
        return {"buffer": len(_buf),
                "dispositivos": dict(_last_seen)}
