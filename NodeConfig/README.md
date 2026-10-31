# SafeCore NodeConfig — FW 3.0  +  PWA de configuracion

Carpeta **aislada** del proyecto principal `SafeCore-IoT/`. Todo lo nuevo vive
aca; el repo principal no se toca. El `SafeCore-IoT/firmware/safecoreNode.ino`
(v2.1) sigue siendo el firmware vigente hasta que apruebes este.

## Que resuelve

Hoy cambiar la red WiFi, la IP del servidor, el serial, el umbral o la tasa
exige recompilar y reflashear. Con FW 3.0 el propio nodo expone una interfaz
web (PWA) desde la que el telefono edita todo, sin cable ni Arduino IDE:

| Campo de BD (`dispositivos`) | Editable desde la PWA en el telefono | Como llega a la BD |
|---|---|---|
| `codigo_serial` | si | el nodo lo envia en cada ingest, el backend lo matchea |
| `firmware_version` | si | ingest reporta el FW (parche del servidor lo persiste) |
| `identificador_unico` | auto (MAC del ESP8266) | ya existente (matchDeviceBySerial) |
| `nombre`, `id_modelo`, `id_zona`, `id_estado`, `fecha_instalacion`, `activo` | no | quedan en el panel `/admin/devices` de FastAPI |
| WiFi/clave, IP:puerto:ruta servidor, umbral, tasa, PIN | si | solo local (EEPROM del nodo) |

## Estructura

```
SafeCore-NodeConfig/
├── firmware/
│   └── nodosafecore/            Arduino IDE v2 exige carpeta homonima al sketch
│       ├── nodosafecore.ino     sketch principal (setup/loop/sensado/comandos)
│       ├── nodosafecore.h       cabecera comun (tipos/globals/prototipos)
│       ├── configStore.ino      estructura persistente EEPROM + defaults v2.1
│       └── webPortal.ino        servidor web + captive portal + mDNS + API JSON
├── parche-servidor/             cambios de FastAPI PREPARADOS PERO SIN APLICAR
├── notas/
│   └── PLAN.md                  plan acordado
└── README.md                    este archivo
```

Nota: el HTML de la PWA vive embebido en PROGMEM dentro de `webPortal.ino`.
No hay archivo `config.html` aparte para que no existan dos copias divergentes.

Nota tecnica: el sketch principal (`nodosafecore.ino`) es el tab queArduino
concatena PRIMERO, por eso las referencias cruzadas a tipos, globals y
funciones de los otros tabs viven en `nodosafecore.h` (incluido al inicio de
cada tab): el orden de concatenacion queda irrelevante para la compilacion.

## Como compilar (Arduino IDE v2)

1. Abrir `firmware/nodosafecore/nodosafecore.ino` (los otros tabs se cargan solos).
2. Placa: **LOLIN(WEMOS) D1 R2 & mini** (la placa fisica es un ESP8266 Wemos D1;
   quedo confirmado via boot ROM: `ets Jan 8 2013` + `load 0x4010f000`).
3. Puerto: `/dev/ttyUSB0` (adaptador FT232). Monitor a **115200 baudios**.
4. Solo alimentacion y grabar. Depués del primer flasheo, ya no se necesita
   mas la PC.
   OJO con el FT232: si la subida falla en "Connecting..." el nodo no entra al
   bootloader automaticamente; en ese caso mantener presionado FLASH (GPIO0),
   tocar RESET, soltar FLASH y reintentar. El GRABAR suele lograrlo solo via
   RTS si tu cableado DTR->GPIO0 est completo.

## Como se usa (flujo telefonico)

**A. Ya conectado a una red (caso comun, ej. hotspot del POCO):**
1. El telefono se conecta a la misma red.
2. Abrir `http://safecore-nodo.local` en el navegador (mDNS responde al nodo).
   Nota: `.local` funciona bien en iOS y desktop con mDNS; Chromium en Android
   no siempre lo resuelve. Alternativa universal: abrir `http://<IP del nodo>`
   (la IP sale en el monitor serie, en el caso de prueba actual
   `10.179.131.53`; con el parche del servidor aplicado, la podria listar el
   panel admin).
3. Ingresar el PIN (defecto **1234**, cambiable) → **Sincronizar**.
4. Editar lo querido → **Guardar**. Se persiste en EEPROM y se aplica al vivo.

**B. En un entorno nuevo (red desconocida o error):**
1. El nodo no logra conectarse: levanta su AP **`SafeCore-XXXX` con clave
   WPA2 `12345678`** (la clave del AP es aparte del PIN `1234` de la pagina).
   FW 3.1.2: sin red conocida, el nodo pasa a **AP puro estable** y solo
   hace ventanas cortas de intento STA (30 s cada ~90 s), porque el SDK del
   ESP8266 degrada el softAP mientras el STA intenta conectar sin exito.
2. Conectar el telefono a ese AP (Android avisara "sin internet": es esperado;
   los datos moviles siguen por otra via) → portal automatico o
   manualmente **`http://192.168.4.1`** (ojo: es 192, no 194).
3. En la PWA: **Escanear redes** → elegir SSID → clave + datos del servidor →
   Guardar. El nodo se conecta al vuelo sin reiniciarse.
4. (Opcional) "Agregar a pantalla de inicio" para dejar la PWA como app
   con icono.

Sobre PWA: service worker y "install prompt" automatico de Chrome exigen
HTTPS; con el nodo serviendo HTTP puro la app se instala igual con los botones
manuales de Chrome/Safari (el manifest + iconos + `apple-mobile-web-app-
capable` ya estan servidos por el nodo). Si algun dia hace falta el prompt
automatico, se puede montar un proxy HTTPS Esta HAProxy/Caddy frente al nodo.

## API JSON del nodo (por si luego se quiere una app nativa)

| Endpoint | Descripcion |
|---|---|
| `GET /api/status` | estado: conectado, ip, rssi, seq, alarma, heap, uptime |
| `GET /api/config?pin=...` | config completa (necesita PIN) |
| `POST /api/config` (pin, ssid, password, host, puerto, ruta, serial, fw, umbral, rate, pin_nuevo) | guarda + aplica + persiste |
| `GET /api/scan` | redes WiFi visibles (ssid/rssi/cifrada) |
| `GET /api/test` | prueba TCP al servidor configurado (ok/ms) |

## Comandos por Monitor Serie (ahora TODO persiste en EEPROM)

`PING   SHOW   FACTORY   RATE=<2..300>   THR=<30..1023>   DEVICE=<serial>
FW=<ver>   WIFI=<ssid>:<clave>   HOST=<ip>[:<puerto>]   RUTA=</x>
PIN=<nuevo>`  (minimo 4 chars)

Mejores respecto a v2.1: persistencia EEPROM con checksum, `WiFi.persistent(false)`,
watchdog (`ESP.wdtEnable`), password opcional en `WIFI=` sin clave, y la version
de FW pasa a ser dato editable (se reporta en cada ingest).

FW 3.1-auto (FW >= 3.1): si el envio al servidor falla 3 veces seguidas
(ej. la IP del hotspot cambio), el nodo pregunta por UDP broadcast
("SAFECORE?" a :5001) y el servidor (utils/discovery.py) le responde con su
IP: el nodo se repara solo y persiste la IP con origen `(auto)`. La IP puesta
manualmente (PWA o `HOST=`) manda hasta que deja de funcionar. Ademas consulta
cada 5 min `/api/nodes/{serial}/config` y publica en `/api/status` y en la
PWA si el nodo esta `registrado | no-registrado | desconocido` en la BD.

FW 3.1.3: el umbral de alarma no acepta valores menores a 30 (THR=0 dejaba
la alarma encendida permanentemente); se valida igual en serie y en la PWA.

Panel `/admin/devices`: cada dispositivo muestra **"Página del nodo"** con la
ultima IP desde la que el nodo envio datos (`data/nodo_ips.json`, lo escribe
el ingest; nota: el enlace funciona solo estando en la misma red del nodo).

Seguridad: el AP exige WPA2 (`12345678`) y la edicion exige PIN (los GET de
status/scan no). Cambiar el PIN por defecto en el primer uso.

## Saparecer el FW viejo

1. Probar FW 3.0: quema `firmware/nodosafecore/` y verificar con el telefono
   y con los comandos serie (`SHOW`).
2. Si se aprueba: mover `SafeCore-IoT/firmware/safecoreNode.ino` + `secrets.h`
   a historial y copiar ahi al sketch nuevo (o directamente trabajar siempre
   desde esta carpeta).
