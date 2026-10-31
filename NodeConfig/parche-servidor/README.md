# Parche servidor — APLICADO a SafeCore-IoT

Estos cambios de FastAPI **fueron aplicados** al repo principal
(`SafeCore-IoT/`) el 24/10/2026:

- `models/devicesModel.py` → `getDeviceBySerial()`
- `models/readingsModel.py` → `updateFirmwareVersion()`
- `controllers/readingsController.py` → `nodeConfig()` en `ingestReadings`
  (metadatos del nodo corren en ambos modos: en-vivo-sin-guardar y
  acumulando; tolerante a BD caida; respuesta agrega campo `bd`)
- `routers/readingRoutes.py` → `GET /api/nodes/{serial}/config`
- `utils/discovery.py` + arranque en `main.py` → listener UDP de
  descubrimiento (el nodo pregunta "SAFECORE?" por broadcast y recibe
  `SAFECORE <ip> <puerto>`)
- `.env`: opcional `SAFECORE_DISCOVERY=0` para desactivar el listener

## Que habilitan una vez aplicados

1. **Sincronización de FW (nodosafe)**: cuando el nodo reporta su version de
   firmware en el `POST /api/ingest`, si difiere de la BD se persiste. Con
   esto, cambiar la version de FW desde la PWA del telefono queda reflejado
   en la columna `dispositivos.firmware_version` automaticamente.
2. **Consulta de registrado**: el endpoint `GET /api/nodes/{serial}/config`
   devuelve datos del registro (nombre, estado, modelo, zona, FW) para que la
   PWA muestre si el nodo ya esta dado de alta. Sin este parche, la PWA
   funciona igual: la consulta solo no llegara y el nodo seguira trabajando.

## Archivos

| Archivo del parche | Destino en SafeCore-IoT |
|---|---|
| `parche_dispositivos.py` | models/devicesModel.py — append al final |
| `parche_readings.py`     | models/readingsModel.py (funcion) + controllers/readingsController.py (4 líneas) |
| `parche_rutas.py`        | controllers/readingsController.py (función) + routers/readingRoutes.py (1 línea) |

## Como aplicar (manual, sanos y lentos)

1. Copiar `parche_dispositivos.py` completo al final de `models/devicesModel.py`
   (ajustar imports si hedding duplicados: getConnection/closeConnection ya
   alla importados — no repetirlos).
2. Copiar la función `updateFirmwareVersion` de `parche_readings.py` al final
   de `models/readingsModel.py`.
3. En `controllers/readingsController.py`:
   - agregar al final la función `nodeConfig` (ver parche_rutas.py),
   - dentra de `ingestReadings`, después de `lec_model.markDeviceAlive(...)`,
     insertar el bloque que persiste el FW (ver parche_readings.py parte 2).
4. En `routers/readingRoutes.py`, agregar la línea de ruta del final de
   `parche_rutas.py`.
5. `python main.py` y verificar con curl:
   `curl http://localhost:8000/api/nodes/SC-001/config`

## Si NUNCA se quiere aplicar

No hay dependencia: el nodo FW 3.0 funciona 100% sobre si mismo
(config/WiFi/servidor/serial local), y el backend actual funciona como hasta
ahora + reconoce el nodo por código serial sin cambios.
