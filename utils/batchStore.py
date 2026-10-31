"""Acumulación de lecturas por intervalo en RAM; envío a BD por lote (promedio por magnitud)."""
import threading
import time
from typing import Any, Callable, Dict, List

from models import readingsModel as lec_model

_MAX_HISTORIAL, _MAX_INTERMEDIO = 6, 2000
_lock = threading.Lock()
_pending: List[Dict[str, Any]] = []
_historial: List[Dict[str, Any]] = []
_intervalo = 60
_persistent_check: Callable[[], bool] = lambda: False
_proximo_envio_ts = 0.0


def start(intervalo_s: int, is_persistent: Callable[[], bool]):
    global _intervalo, _persistent_check, _proximo_envio_ts
    with _lock:
        _intervalo = max(5, int(intervalo_s))
        _persistent_check = is_persistent
        _proximo_envio_ts = time.time() + _intervalo
        activo = _hilo is not None
    if not activo:
        _arrancarHilo()


def add(device_serial: str, fw: str | None, seq: int,
        readings: List[Dict[str, Any]]) -> int:
    ts = time.time()
    with _lock:
        for r in readings:
            _pending.append({"codigo_serial": device_serial, "fw": fw, "seq": seq,
                             "magnitud": r["tipo"], "valor": r["valor"],
                             "calidad": r["calidad"], "_ts": ts})
        return len(_pending)


def snapshot() -> Dict[str, Any]:
    ahora = time.time()
    with _lock:
        lote = [{k: v for k, v in it.items() if not k.startswith("_")}
                for it in _pending]
        return {"intervalo_s": _intervalo,
                "modo": "persistente" if _persistent_check() else "en-vivo-sin-guardar",
                "segundos_para_envio": max(0, round(_proximo_envio_ts - ahora)),
                "pendientes": len(lote), "lote_actual": lote,
                "historial": list(reversed(_historial))}


def magStats(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grupo: Dict[str, Dict[str, Any]] = {}
    for it in items:
        g = grupo.setdefault(it["magnitud"], {"validos": [], "dudosos": []})
        (g["validos"] if it["calidad"] == "valida" else g["dudosos"]).append(it["valor"])
    stats = []
    for magnitud, g in grupo.items():
        muestras = g["validos"] if g["validos"] else g["dudosos"]
        stats.append({"magnitud": magnitud,
                      "promedio": round(sum(muestras) / len(muestras), 2),
                      "calidad": "valida" if g["validos"] else "dudosa",
                      "muestras": len(muestras)})
    return stats


def _enviar(lote: List[Dict[str, Any]]):
    promedios, errores = [], []
    grupos: Dict[str, List[Dict[str, Any]]] = {}
    for it in lote:
        grupos.setdefault(it["codigo_serial"], []).append(it)
    for serial, items in grupos.items():
        try:
            dev = lec_model.getDeviceBySerial(serial)
            if dev is None:
                errores.append(f"{serial}: dispositivo no existe en la BD")
                continue
            if not dev["activo"]:
                # HU-014: dispositivos dados de baja no acumulan lecturas
                # (el lote se descarta, no se re-encola).
                errores.append(f"{serial}: dispositivo no activo")
                continue
            lec_model.markDeviceAlive(dev["id_dispositivo"])
            enviadas: List[str] = []
            for m in magStats(items):
                spec = lec_model.MAGNITUDES[m["magnitud"]]
                id_mag = lec_model.ensureMagnitude(spec["nombre"], spec["unidad"],
                                                   spec["simbolo"])
                id_sens = lec_model.ensureSensorForMagnitude(dev["id_dispositivo"], id_mag)
                lec_model.insertReading(m["promedio"], m["calidad"], id_sens, id_mag)
                enviadas.append(m["magnitud"])
                promedios.append({**m, "dispositivo": serial})
            pend_mags = {m["magnitud"] for m in magStats(items)} - set(enviadas)
            if pend_mags:
                with _lock:
                    _pending[:0] = [it for it in items if it["magnitud"] in pend_mags]
        except Exception as e:
            errores.append(f"{serial}: {e}")
            with _lock:
                _pending[:0] = items
    return promedios, errores


def _proceso():
    ahora = time.time()
    with _lock:
        lote = _pending[:_MAX_INTERMEDIO]
        del _pending[:len(lote)]
    if not lote:
        return
    detalle = _pendienteLegible(lote)
    persistent = _persistent_check()
    if persistent:
        promedios, errores = _enviar(lote)
        entrada = {"cuando": _fecha(ahora), "resultado": "bd" if not errores else "error",
                   "recibidas": len(lote), "promedios": promedios,
                   "detalle": detalle, "errores": errores}
    else:
        entrada = {"cuando": _fecha(ahora), "resultado": "vivo", "recibidas": len(lote),
                   "promedios": [], "detalle": detalle,
                   "nota": "Modo vivo: lote descartado sin envío a la BD"}
    with _lock:
        _historial.append(entrada)
        del _historial[:-_MAX_HISTORIAL]


def _pendienteLegible(lote: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"codigo_serial": it["codigo_serial"], "fw": it["fw"], "seq": it["seq"],
             "magnitud": it["magnitud"], "valor": it["valor"], "calidad": it["calidad"],
             "fecha_hora": _fecha(it["_ts"])} for it in lote]


def _fecha(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


_hilo: threading.Thread | None = None


def _arrancarHilo():
    global _hilo
    with _lock:
        if _hilo is not None:
            return
        _hilo = threading.Thread(target=_bucle, daemon=True)
    _hilo.start()


def _bucle():
    global _proximo_envio_ts
    while True:
        time.sleep(_intervalo)
        with _lock:
            _proximo_envio_ts = time.time() + _intervalo
        try:
            _proceso()
        except Exception:
            pass
