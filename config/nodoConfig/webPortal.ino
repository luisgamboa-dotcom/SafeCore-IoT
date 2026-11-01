// webPortal.ino — web del nodo SafeCore (FW 3.0-portal): sirve la PWA embebida en PROGMEM con la que el telefono configura todo (red WiFi, servidor, serial, FW, umbral, tasa y PIN via http://safecore-nodo.local o el AP "SafeCore-XXXX"), mantiene los endpoints JSON /api/status /api/config (lectura y guardado con PIN obligatorio) /api/scan /api/test, el captive portal con DNS wildcard y mDNS; las URLs desconocidas redirigen al portal cuando no hay internet.
#include "nodosafecore.h"

ESP8266WebServer servidor(80);
DNSServer dnsPortal;
char nombreAp[24];

unsigned long ultimaLectura = 0;
unsigned long ultimoIntentoWiFi = 0;
unsigned long seqTotal = 0;
unsigned long arranqueMs = 0;
bool ultimoEnvioOk = false;
int  ultimoCodigoHttp = 0;
bool alarmaActiva = false;
String origenHost = "manual";
String estadoBD = "desconocido";

static const char PAGINA_HTML[] PROGMEM = R"HTML(
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SafeCore Nodo</title>
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#0d1b2a">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="icon" href="/icon-192.png">
<style>
body{margin:0;font-family:system-ui,sans-serif;background:#0d1b2a;color:#e8ecf1}
main{max-width:540px;margin:0 auto;padding:16px}
h1{font-size:1.15rem;display:flex;align-items:center;gap:.55rem;margin:.2rem 0}
.dot{width:10px;height:10px;border-radius:50%;background:#555;flex:none}
.dot.ok{background:#2dd4a7}.dot.bad{background:#e05252}
.card{background:#16283f;border:1px solid #234065;border-radius:12px;padding:14px;margin:12px 0}
label{display:block;margin:10px 0 4px;font-size:.82rem;color:#9fb3c8}
input{font-size:1rem;width:100%;box-sizing:border-box;padding:10px;border-radius:8px;
      border:1px solid #2e4a6b;background:#0d1b2a;color:#e8ecf1}
button{font-size:1rem;width:100%;box-sizing:border-box;padding:10px;border-radius:8px;
       border:none;background:#1d9bf0;color:#fff;font-weight:600;margin-top:12px;cursor:pointer}
button.sec{background:#234065}
.fila{display:flex;gap:10px}.fila>div{flex:1}
#estado{font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.55;
        color:#9fb3c8;white-space:pre-wrap;word-break:break-all}
#msg{margin-top:10px;font-size:.88rem;color:#2dd4a7;min-height:1.3em}
#redes button{margin:6px 0 0;background:#0d1b2a;border:1px solid #2e4a6b;
              font-weight:400;text-align:left;font-size:.9rem}
</style>
</head>
<body>
<main>
<h1><span class="dot" id="dot"></span> SafeCore Nodo</h1>

<div class="card"><div id="estado">cargando&hellip;</div></div>

<div class="card">
<b>Configuraci&oacute;n</b>
<label>Red WiFi (SSID)</label><input id="ssid" autocomplete="off">
<label>Contrase&ntilde;a WiFi (vac&iacute;a = mantener la actual)</label>
<input id="password" type="password" placeholder="&bull;&bull;&bull;&bull;&bull;&bull;" autocomplete="off">
<div class="fila">
<div><label>Servidor (host o IP)</label><input id="host"></div>
<div><label>Puerto</label><input id="puerto" inputmode="numeric"></div>
</div>
<label>Ruta API</label><input id="ruta">
<div class="fila">
<div><label>C&oacute;digo serial</label><input id="serial"></div>
<div><label>Versi&oacute;n FW</label><input id="fw"></div>
</div>
<div class="fila">
<div><label>Umbral alarma (gas)</label><input id="umbral" inputmode="numeric"></div>
<div><label>Enviar cada (segundos)</label><input id="rate" inputmode="numeric"></div>
</div>
<label>PIN actual</label><input id="pin" type="password" inputmode="numeric">
<label>PIN nuevo (opcional)</label><input id="pin_nuevo" type="password" inputmode="numeric">
<button id="sincronizar" class="sec">Sincronizar</button>
<button id="escanear" class="sec">Escanear redes WiFi</button>
<button id="probar" class="sec">Probar servidor</button>
<button id="guardar">Guardar configuraci&oacute;n</button>
<div id="redes"></div>
<div id="msg"></div>
</div>
</main>
<script>
const $ = id => document.getElementById(id);

function setMsg(t){ $("msg").textContent = t; }

async function cargarEstado(){
  try{
    const r = await fetch("/api/status");
    const d = await r.json();
    $("dot").className = "dot " + (d.conectado ? "ok" : "bad");
    $("estado").textContent =
      "red:      " + (d.conectado ? "OK (" + (d.rssi) + " dBm)" : "sin conexion") + "\n" +
      "wifi:     " + (d.ssid || "-") + "   ip: " + (d.ip || "-") + "\n" +
      "portal:   " + d.ap + "   ip AP: " + d.ap_ip + "\n" +
      "servidor: " + (d.host || "-") + "\n" +
      "bd:       " + (d.bd || "desconocido") + "\n" +
      "serial:   " + (d.mac) + "\n" +
      "envio:    " + (d.ultimo_envio ? "OK" : (d.ultimo_http ? "fallo HTTP " + d.ultimo_http : "-")) +
      "   seq: " + (d.seq) + "\n" +
      "alarma:   " + (d.alarma ? "ON" : "off") + "\n" +
      "encendido: " + (d.uptime_s) + " s   libre: " + (d.heap) + " B";
  }catch(e){ $("estado").textContent = "nodo no responde"; }
}

async function sincronizar(){
  const pin = $("pin").value.trim();
  if(!pin){ setMsg("Ingresá el PIN y tocá Sincronizar."); return; }
  sessionStorage.setItem("pin", pin);
  try{
    const r = await fetch("/api/config?pin=" + encodeURIComponent(pin));
    if(r.status === 401){ setMsg("PIN incorrecto."); return; }
    const d = await r.json();
    $("ssid").value = d.ssid; $("password").value = d.password;
    $("host").value = d.host; $("puerto").value = d.puerto;
    $("ruta").value = d.ruta;  $("serial").value = d.serial;
    $("fw").value = d.fw;      $("umbral").value = d.umbral;
    $("rate").value = d.rate;
    setMsg("Config cargada.");
  }catch(e){ setMsg("No llego al nodo."); }
}

async function guardar(){
  const pin = $("pin").value.trim() || sessionStorage.getItem("pin") || "";
  if(!pin){ setMsg("Ingresá el PIN."); return; }
  const p = new URLSearchParams();
  p.set("pin", pin);
  p.set("ssid", $("ssid").value.trim());
  p.set("password", $("password").value);
  p.set("host", $("host").value.trim());
  p.set("puerto", $("puerto").value.trim());
  p.set("ruta", $("ruta").value.trim());
  p.set("serial", $("serial").value.trim());
  p.set("fw", $("fw").value.trim());
  p.set("umbral", $("umbral").value.trim());
  p.set("rate", $("rate").value.trim());
  const nuevo = $("pin_nuevo").value;
  if(nuevo) p.set("pin_nuevo", nuevo);
  try{
    const r = await fetch("/api/config", {method:"POST", body:p});
    const d = await r.json();
    setMsg(d.ok ? "Guardado y aplicado." : "Error: " + (d.error || "?"));
    $("pin_nuevo").value = "";
    cargarEstado();
  }catch(e){ setMsg("No llego al nodo."); }
}

async function escanear(){
  $("redes").innerHTML = "escaneando&hellip;";
  try{
    const r = await fetch("/api/scan");
    const d = await r.json();
    const lista = document.getElementById("redes");
    lista.innerHTML = "";
    d.redes.forEach(re => {
      const b = document.createElement("button");
      b.textContent = re.ssid + "  (" + re.rssi + " dBm" + (re.cifrada ? ", cifrada" : "") + ")";
      b.onclick = () => { $("ssid").value = re.ssid; $("password").focus(); };
      lista.appendChild(b);
    });
    if(!d.redes.length) lista.innerHTML = "sin redes con nombre visibles";
  }catch(e){ $("redes").innerHTML = "fallo el escaneo"; }
}

async function probarServidor(){
  setMsg("probando servidor&hellip;");
  try{
    const r = await fetch("/api/test");
    const d = await r.json();
    setMsg(d.ok ? "Servidor alcanzable en " + d.ms + " ms." : "Servidor NO alcanzable.");
  }catch(e){ setMsg("No llego al nodo."); }
}

window.addEventListener("load", () => {
  $("sincronizar").onclick = sincronizar;
  $("guardar").onclick = guardar;
  $("escanear").onclick = escanear;
  $("probar").onclick = probarServidor;
  cargarEstado();
  setInterval(cargarEstado, 5000);
  if(navigator.serviceWorker){ navigator.serviceWorker.register("/sw.js").catch(()=>{}); }
});
</script>
</body>
</html>
)HTML";

static const char MANIFIESTO_JSON[] PROGMEM = R"JSON(
{"name":"SafeCore Nodo","short_name":"SafeCore","start_url":"/","scope":"/",
 "display":"standalone","background_color":"#0d1b2a","theme_color":"#0d1b2a",
 "icons":[{"src":"/icon-192.png","sizes":"192x192","type":"image/png"}]}
)JSON";

static const char SW_JS[] PROGMEM = R"SWJS(
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => self.clients.claim());
self.addEventListener("fetch", e => {
  e.respondWith(fetch(e.request)
    .catch(() => new Response("Sin conexion con el nodo",
            {status: 503, statusText: "offline"})));
});
)SWJS";

static const char ICONO_B64[] PROGMEM = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAABkElEQVR42u3XMQ0AIAxFwRpAAQ7wL4qBBQdVwMLUpJecgp83tDHmgm9hAgSEgBAQAgIBISAEhIBAQAgIASEgEBACQkAICASEgBAQAkJAICAEhIAQEAgIASEgBAQCQkAICAGBgBAQAkJACAgEhIAQEAICASEgBISAQEAICAEhIBAQAkJACAgEhIAQEAJCQCAgBISAEBAICAEhIAQEAkJACAgBgYAQEAJCQAgIBISAEBACAgEhIASEgFrZ574YR0ACEpCABFS5G1MISEACEpCABCQgASEgAQnIGy8gAQlIQPYRkDtJQAISkIAEJCAEJCABCUhAxb933QhIQAISkIAQEAgIASEgBISATICAEBACQkAgIASEgBAQCAgBISAEBAJCQAgIAYGAEBACQkAICASEgBAQAgIBISAEhIBAQAgIASEgEBACQkAICAGBgBAQAkJAICAEhIAQEAgIASEgBAQCQkAICAGBgBAQAkJACAgEhIAQEAICASEgBISAQEAICAEhIBAQAkJACAgBgYAQEAKikQRAFFdck6GSaQAAAABJRU5ErkJggg==";

int8_t valB64(char c) {
  if (c >= 'A' && c <= 'Z') return c - 'A';
  if (c >= 'a' && c <= 'z') return c - 'a' + 26;
  if (c >= '0' && c <= '9') return c - '0' + 52;
  if (c == '+') return 62;
  if (c == '/') return 63;
  return -1;
}

size_t decodeB64(const char* src, uint8_t* dst, size_t cap) {
  size_t out = 0;
  uint32_t acc = 0;
  int bits = 0;
  for (size_t i = 0; ; i++) {
    char c = pgm_read_byte(src + i);
    if (c == 0) break;
    int8_t v = valB64(c);
    if (v < 0) continue;
    acc = (acc << 6) | (uint32_t)v;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      if (out < cap) dst[out++] = (uint8_t)((acc >> bits) & 0xFF);
    }
  }
  return out;
}

void copiaSeg(char* dst, size_t tam, const String& s) {
  strncpy(dst, s.c_str(), tam - 1);
  dst[tam - 1] = '\0';
}

void hostManual() {
  origenHost = "manual";
}

bool pinValido() {
  return servidor.arg("pin") == String(CFG.pin);
}

String escJson(const String& s) {
  String r = "";
  for (unsigned int i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') r += '\\';
    if (c < 32 || c > 126) { r += ' '; continue; }
    r += c;
  }
  return r;
}

void pinIncorrecto() {
  servidor.send(401, "application/json",
                "{\"ok\":false,\"error\":\"PIN incorrecto\"}");
}

void hRaiz()    { servidor.send_P(200, "text/html", PAGINA_HTML); }
void hManifiesto(){ servidor.send_P(200, "application/manifest+json", MANIFIESTO_JSON); }
void hSw()      { servidor.send_P(200, "application/javascript", SW_JS); }

void hIcono() {
  static uint8_t bufIcono[1024];
  size_t n = decodeB64(ICONO_B64, bufIcono, sizeof(bufIcono));
  servidor.send(200, "image/png", bufIcono, n);
}

void hEstado() {
  String r = "{\"ok\":true";
  r += ",\"conectado\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false");
  r += ",\"ssid\":\"" + String(WiFi.SSID()) + "\"";
  r += ",\"ip\":\"" + WiFi.localIP().toString() + "\"";
  r += ",\"ap\":\"" + String(nombreAp) + "\"";
  r += ",\"ap_ip\":\"" + WiFi.softAPIP().toString() + "\"";
  r += ",\"mac\":\"" + WiFi.macAddress() + "\"";
  r += ",\"host\":\"" + escJson(String(CFG.host)) + ":" + String(CFG.puerto) +
       " (" + origenHost + ")\"";
  r += ",\"bd\":\"" + escJson(estadoBD) + "\"";
  r += ",\"rssi\":" + String(WiFi.RSSI());
  r += ",\"uptime_s\":" + String((millis() - arranqueMs) / 1000UL);
  r += ",\"heap\":" + String(ESP.getFreeHeap());
  r += ",\"seq\":" + String(seqTotal);
  r += ",\"alarma\":" + String(alarmaActiva ? "true" : "false");
  r += ",\"ultimo_envio\":" + String(ultimoEnvioOk ? "true" : "false");
  r += ",\"ultimo_http\":" + String(ultimoCodigoHttp);
  r += "}";
  servidor.send(200, "application/json", r);
}

void hLeerConfig() {
  if (!pinValido()) { pinIncorrecto(); return; }
  String r = "{\"ok\":true";
  r += ",\"ssid\":\"" + escJson(String(CFG.ssid)) + "\"";
  r += ",\"password\":\"" + escJson(String(CFG.password)) + "\"";
  r += ",\"host\":\"" + escJson(String(CFG.host)) + "\"";
  r += ",\"puerto\":" + String(CFG.puerto);
  r += ",\"ruta\":\"" + escJson(String(CFG.ruta)) + "\"";
  r += ",\"serial\":\"" + escJson(String(CFG.serial)) + "\"";
  r += ",\"fw\":\"" + escJson(String(CFG.fw)) + "\"";
  r += ",\"umbral\":" + String(CFG.umbral);
  r += ",\"rate\":" + String(CFG.rate_s);
  r += "}";
  servidor.send(200, "application/json", r);
}

void hEscanear() {
  int n = WiFi.scanNetworks(false, true);
  String r = "{\"ok\":true,\"redes\":[";
  bool primero = true;
  for (int i = 0; i < n; i++) {
    String ssid = WiFi.SSID(i);
    if (ssid.length() == 0) continue;
    if (!primero) r += ",";
    r += "{\"ssid\":\"" + escJson(ssid) + "\",\"rssi\":" + String(WiFi.RSSI(i)) +
         ",\"cifrada\":" + String(WiFi.encryptionType(i) != ENC_TYPE_NONE ? "true" : "false") + "}";
    primero = false;
  }
  r += "]}";
  WiFi.scanDelete();
  servidor.send(200, "application/json", r);
}

void hProbarServidor() {
  WiFiClient cli;
  unsigned long t0 = millis();
  bool ok = cli.connect(CFG.host, CFG.puerto);
  unsigned long ms = millis() - t0;
  cli.stop();
  String r = "{\"ok\":" + String(ok ? "true" : "false") +
             ",\"ms\":" + String((unsigned long)ms) + "}";
  servidor.send(200, "application/json", r);
}

void hGuardarConfig() {
  if (!pinValido()) { pinIncorrecto(); return; }

  bool cambioRed = false;
  String ssidArg  = servidor.arg("ssid");
  String passArg  = servidor.arg("password");
  String hostArg  = servidor.arg("host");
  String rutaArg  = servidor.arg("ruta");
  String serialArg= servidor.arg("serial");
  String fwArg    = servidor.arg("fw");
  String pinArg   = servidor.arg("pin_nuevo");
  int puertoArg   = servidor.arg("puerto").toInt();
  int umbralArg   = servidor.arg("umbral").toInt();
  int rateArg     = servidor.arg("rate").toInt();

  if (ssidArg.length())
    cambioRed |= (ssidArg != String(CFG.ssid));
  if (passArg.length())
    cambioRed |= (passArg != String(CFG.password));

  if (ssidArg.length()) copiaSeg(CFG.ssid, sizeof(CFG.ssid), ssidArg);
  if (passArg.length()) copiaSeg(CFG.password, sizeof(CFG.password), passArg);
  if (hostArg.length()) {
    copiaSeg(CFG.host, sizeof(CFG.host), hostArg);
    hostManual();
  }
  if (rutaArg.length() && rutaArg[0] == '/')
    copiaSeg(CFG.ruta, sizeof(CFG.ruta), rutaArg);
  if (serialArg.length()) copiaSeg(CFG.serial, sizeof(CFG.serial), serialArg);
  if (fwArg.length()) copiaSeg(CFG.fw, sizeof(CFG.fw), fwArg);
  if (puertoArg > 0 && puertoArg < 65536) CFG.puerto = (uint16_t)puertoArg;
  if (servidor.hasArg("umbral") && umbralArg >= 30 && umbralArg <= 1023)
    CFG.umbral = umbralArg;
  if (servidor.hasArg("rate") && rateArg >= 2 && rateArg <= 300)
    CFG.rate_s = (uint16_t)rateArg;
  if (pinArg.length() >= 4 && pinArg.length() < (int)sizeof(CFG.pin))
    copiaSeg(CFG.pin, sizeof(CFG.pin), pinArg);

  escribirConfig();
  if (cambioRed) aplicarRedNueva(CFG.ssid, CFG.password);

  servidor.send(200, "application/json",
                "{\"ok\":true,\"msg\":\"guardado\"}");
}

void hRedirigePortal() {
  if (WiFi.status() != WL_CONNECTED) {
    servidor.sendHeader("Location",
                        String("http://") + WiFi.softAPIP().toString() + "/", true);
    servidor.send(302, "text/plain", "");
  } else {
    servidor.send(404, "text/plain", "No existe");
  }
}

void atenderWeb() {
  dnsPortal.processNextRequest();
  servidor.handleClient();
}

void lanzarPortal() {
  String mac = WiFi.softAPmacAddress();
  String sufijo = "";
  for (int i = mac.length() - 1; i >= 0 && sufijo.length() < 4; i--) {
    char c = mac[i];
    if (isGraph(c) && c != ':') sufijo = String(c) + sufijo;
  }
  snprintf(nombreAp, sizeof(nombreAp), "SafeCore-%s", sufijo.c_str());

  WiFi.softAP(nombreAp, CLAVE_AP);
  dnsPortal.start(53, "*", WiFi.softAPIP());

  servidor.on("/", HTTP_GET, hRaiz);
  servidor.on("/manifest.webmanifest", HTTP_GET, hManifiesto);
  servidor.on("/sw.js", HTTP_GET, hSw);
  servidor.on("/icon-192.png", HTTP_GET, hIcono);
  servidor.on("/apple-touch-icon.png", HTTP_GET, hIcono);
  servidor.on("/api/status", HTTP_GET, hEstado);
  servidor.on("/api/config", HTTP_GET, hLeerConfig);
  servidor.on("/api/config", HTTP_POST, hGuardarConfig);
  servidor.on("/api/scan", HTTP_GET, hEscanear);
  servidor.on("/api/test", HTTP_GET, hProbarServidor);
  servidor.onNotFound(hRedirigePortal);
  servidor.begin();
}
