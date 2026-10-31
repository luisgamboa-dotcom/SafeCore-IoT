# PLAN.md — Configuracion remota del nodo SafeCore (acordado con Luis)

## Contexto confirmado

- Placa fisica: **ESP8266** (familia Wemos D1), CONFIRMADO por boot ROM leido
  por serie: `ets Jan  8 2013, rst cause:2`, `load 0x4010f000`, `rf cal sector`.
  No es un ESP32 (aunque se creia). El codigo actual ya era correcto para el chip.
- Conexion a PC: adaptador FTDI FT232 en `/dev/ttyUSB0`, 115200 baudios; el
  nodo tenia corriendo el FW v2.1 propio del repo al momento del diagnostico.
- Firmware actual (SafearCore-IoT/firmware/safecoreNode.ino v2.1): todo
  configurable (red, IP servidor, serial) esta hardcodeado y exige reflash;
  `RATE/THR/DEVICE` por serial existen pero no persisten al reboot.

## Decisiones de Lucho

| Tema | Decision |
|---|---|
| Interfaz movil | **PWA instalable** (pag. web del nodo + manifest + icono); una app nativa podria venir depois sobre la misma API JSON |
| Metadatos BD | `codigo_serial` y `firmware_version` editable desde la interfaz del nodo; el resto (nombre, modelo, zona, estado, fecha_instalacion, activo) por el panel `/admin/devices` |
| Portal AP | Siempre activo (AP+STA): sta conectando y captive portal de rescate |
| Aislamiento | Todo nuevo en `SafeCore-NodeConfig/`, SIN tocar el repositorio; los cambios del servidor quedan como parche no aplicado |

## Alcances y como se implemento

### Firmware (FW 3.0-portal) — firmware/nodosafecore/

1. `configStore.ino`: struct `NodoConfig` en EEPROM con magic/version/CRC8 y
   defaults iguales al estado actual del repo (POCO / 10.115.20.30 / SC-001 /
   THP 200 / rate 10 / pin 1234). Si el bloque no valido -> defaults.
2. `webPortal.ino`: `ESP8266WebServer` (puerto 80) + `DNSServer` Wildcard ->
   captive portal cuando no hay internet; mDNS `safecore-nodo.local`; API JSON
   (status/config POST+get/scan/test); PWA servida desde PROGMEM con manifest,
   icono PNG generico (192px) y service worker; AP "SafeCore-XXXX" abierto es
   obligatorio PIN para editar.
3. `nodosafecore.ino` (main): loop integro — sensado v2.1 intacto (MQ-2 con
   promedio 5, DHT22 3 reintentos, alarma local, envio por HTTP con descarte
   si no hay red); comandos por serie ahora PERSISTEN en EEPROM; cuali configur
   nueva de WiFi se aplica al vivo y sin reset; `WiFi.persistent(false)`;
   watchdog activado.

### Parche servidor (no aplicado) — parche-servidor/

- GET `/api/nodes/{serial}/config`: datos de registro del nodo (read del BD).
- Persistencia automatica de `firmware_version` al momento del ingest.
- Funcion `getDeviceBySerial` + `updateFirmwareVersion` en models.

### No hecho (o posoeho)

- Endpooint de escritura de nombre/modelo/etc desde la PWA: IBAN por el
  panel administrativo ya existente.
- App nativa Android: la API JSON del nodo ya la habilita cuando haga falta.
- Prompt automatico de instalacion PWA: requiere HTTPS frente al nodo.

## Verificacion

1. Compilar con Arduino IDE v2 (board LOLIN(WEMOS) D1 R2 & mini, puerto
   /dev/ttyUSB0). firmware: si una libreiremake metha faltante, instalar por el
   Library Manager (todas son oficiales del core ESP8266: WiFi, HTTPClient,
   WebServer, mDNS, DNSServer, EEPROM, DHT sensorlibrary de Adafruit).
2. Al boot: monitor serie 115200 debe listar "# SafeCore listo FW=3.0-portal"
   + portal URLs. `SHOW` lista la config.
3. Del telefono: conectar a la red, abrir `http://safecore-nodo.local`,
   PIN 1234 -> Sincronizar; cambiar algo (ej. rate 15) -> Guardar.
   Apagar/encender nodo y verificar con `SHOW` que persistio.
4. Probar captive portal: FACTORY + quitar_wifi (WIFI= apagar? -> Borrar red
   haciendo `WIFI=` sin ssid valid -> fallback a AP, el telefono abre portal).
5. Probar servidor con "Probar servidor" en la PWA y `POST /api/ingest`
   visladado del log del backend FastAPI.
