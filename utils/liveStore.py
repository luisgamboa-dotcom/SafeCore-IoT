"""Buffer en vivo (solo memoria): la ingesta NO se guarda en disco/DB."""
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
                "valor": r["valor"],
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
    return [{k: v for k, v in d.items() if not k.startswith("_")} for d in out]
