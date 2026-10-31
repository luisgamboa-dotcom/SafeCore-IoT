# parche_readings.py — cambios para el ingest del nodo Smart (FW 3.0)
# SIN APLICAR: ver parche-servidor/README.md

```python
# ---------- 1) models/readingsModel.py — agrregar al FINAL ----------


def updateFirmwareVersion(id_dispositivo, fw):
    """Persiste la versión de FW reportada por el nodo (editable desde su PWA)."""
    conn = getConnection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE dispositivos SET firmware_version = %s"
                    " WHERE id_dispositivo = %s", (fw, id_dispositivo))
        conn.commit()
    finally:
        closeConnection(conn, cur)


# ---------- 2) controllers/readingsController.py — en def
# ingestReadings(payload), justo después de lec_model.markDeviceAlive(...) ----------

        # FW reportado por el nodo: persistirlo si es distinto
        if payload.fw and payload.fw != dev.get("firmware_version"):
            try:
                lec_model.updateFirmwareVersion(dev["id_dispositivo"], payload.fw)
            except Exception:
                pass  # no tira abajo el ingest si falla el UPDATE
```
