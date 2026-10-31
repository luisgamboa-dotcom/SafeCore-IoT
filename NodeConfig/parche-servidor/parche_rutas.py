# parche_rutas.py — agregar front-end de los endpoints del nodo
# SIN APLICAR: ver parche-servidor/README.md

```python
# ---------- 1) controllers/readingsController.py — agrregar cerca del final ----------


def nodeConfig(serial: str):
    """Datos del registro que consulta el nodo IoT (PWA / config)."""
    dev = dev_model.getDeviceBySerial(serial)
    if dev is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "registrado": False,
                     "error": f"El nodo '{serial}' no está registrado "
                              "en la base de datos. Crealo en dispositivos con "
                              "ese código serial."})
    return {"ok": True, "registrado": True,
            "codigo_serial": dev["codigo_serial"],
            "nombre": dev["nombre"],
            "estado": dev["estado"],
            "modelo": dev["nombre_modelo"],
            "zona": dev["zona"],
            "firmware_version": dev["firmware_version"],
            "identificador_unico": dev["identificador_unico"]}


# ---------- 2) routers/readingRoutes.py — agrregar una línea ----------

readings_router.get("/api/nodes/{serial}/config")(readingsController.nodeConfig)
```

# Nota: /api/nodes/... queda SIN auth de sesión a fines de probar
# rápidamente el nodo. Si prefiere restringirlo: agregar los mêmes Depends
# (session_cookie/verificador) que getLiveReadings y pasar el serial por query.
