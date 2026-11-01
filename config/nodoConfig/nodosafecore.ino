// nodosafecore.ino — sketch principal del nodo autonomo SafeCore IoT (FW 3.0-portal, reemplazo del v2.1 sin reflashear): lee MQ-2/DHT22, gestiona la radio AP/STA con el portal de configuracion y la PWA del telefono (http://safecore-nodo.local o AP SafeCore-XXXX), persiste toda la configuracion en EEPROM via EEPROM (tambien editable por Monitor Serie: PING SHOW FACTORY RATE THR DEVICE FW WIFI HOST RUTA PIN), envia cada RATE segundos el JSON a POST host:puerto/ruta (/api/ingest), repara la IP del servidor por UDP si falla 3 veces (broadcast "SAFECORE?"; utils/discovery.py responde) y consulta cada 5 min el registro en la BD, manteniendo la alarma local activa sin WiFi ni servidor.
#include "nodosafecore.h"

const int MUESTRAS_MQ2 = 5;
bool mdnsIniciado = false;

const int PUERTO_DESCUBRE = 5001;
const unsigned long MS_PREGUNTA_DESCUBRE     = 2000;
const unsigned long MS_VENTANA_DESCUBRE      = 15000;
const unsigned long MS_REINTENTO_DESCUBRE    = 5UL * 60UL * 1000UL;
const unsigned long MS_CONSULTA_BD           = 5UL * 60UL * 1000UL;

static WiFiUDP udp;
static bool udpIniciado = false;
static bool descubriendo = false;
static unsigned long inicioDescubreMs = 0;
static unsigned long ultimoPktDescubreMs = 0;
static unsigned long ultimoIntentoDescubreMs = 0;
static unsigned long ultimaConsultaBDMs = 0;
static int fallosSeguidos = 0;

void marcarEnvioOk() { fallosSeguidos = 0; }

void marcarEnvioFallido() { fallosSeguidos++; }

const unsigned long MS_VENTANA_STA  = 30000UL;
const unsigned long MS_CICLO_AP_STA = 90000UL;

enum { R_TRYING = 0, R_AP_ONLY = 1 };
static int modoRadio = R_TRYING;
static unsigned long iniVentanaAPSTA = 0;
static unsigned long proximaVentanaMs = 0;

void aplicarRedNueva(const char* ssid, const char* pass) {
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(ssid, pass);
  ultimoIntentoWiFi = millis();
  iniVentanaAPSTA = ultimoIntentoWiFi;
  modoRadio = R_TRYING;
  Serial.print("# WiFi -> ");
  Serial.println(ssid);
}

void gestionarModoRadio() {
  bool conectado = (WiFi.status() == WL_CONNECTED);
  unsigned long ahora = millis();

  if (conectado) {
    if (WiFi.getMode() != WIFI_AP_STA) WiFi.mode(WIFI_AP_STA);
    modoRadio = R_TRYING;
    iniVentanaAPSTA = 0;
    return;
  }

  if (CFG.ssid[0] == '\0') {
    if (WiFi.getMode() != WIFI_AP) WiFi.mode(WIFI_AP);
    modoRadio = R_AP_ONLY;
    return;
  }

  if (modoRadio == R_TRYING) {
    if (iniVentanaAPSTA == 0) iniVentanaAPSTA = ahora;
    if (ahora - iniVentanaAPSTA >= MS_VENTANA_STA) {
      WiFi.mode(WIFI_AP);
      WiFi.softAP(nombreAp, CLAVE_AP);
      modoRadio = R_AP_ONLY;
      iniVentanaAPSTA = 0;
      proximaVentanaMs = ahora + MS_CICLO_AP_STA;
      Serial.println("# AP puro (portal estable); reintento WiFi en 90s");
    }
    return;
  }

  if (ahora >= proximaVentanaMs) {
    WiFi.mode(WIFI_AP_STA);
    WiFi.begin(CFG.ssid, CFG.password);
    modoRadio = R_TRYING;
    iniVentanaAPSTA = ahora;
    Serial.print("# WiFi intentando ");
    Serial.println(CFG.ssid);
  }
}

int leerMQ2Promedio() {
  long suma = 0;
  for (int i = 0; i < MUESTRAS_MQ2; i++) {
    suma += analogRead(PIN_MQ2);
    delay(20);
  }
  return (int)(suma / MUESTRAS_MQ2);
}

bool enviarPorWiFi(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) return false;
  WiFiClient cliente;
  HTTPClient http;
  String url = String("http://") + CFG.host + ":" + CFG.puerto + CFG.ruta;
  http.begin(cliente, url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);
  ultimoCodigoHttp = http.POST(payload);
  http.end();
  bool ok = (ultimoCodigoHttp >= 200 && ultimoCodigoHttp < 300);
  if (ok) {
    marcarEnvioOk();
  } else {
    marcarEnvioFallido();
  }
  return ok;
}

void empezarDescubre(unsigned long ahora) {
  if (descubriendo) return;
  descubriendo = true;
  inicioDescubreMs = ahora;
  ultimoPktDescubreMs = 0;
  ultimoIntentoDescubreMs = ahora;
  Serial.println("# Servidor no responde: buscando por UDP...");
}

void atenderDescubrimiento() {
  unsigned long ahora = millis();
  if (WiFi.status() != WL_CONNECTED) return;
  if (!udpIniciado) {
    udp.begin(PUERTO_DESCUBRE);
    udpIniciado = true;
  }

  int paq = udp.parsePacket();
  if (paq > 0) {
    char buf[96];
    int n = udp.read(buf, sizeof(buf) - 1);
    if (n > 0) {
      buf[n] = '\0';
      if (strncmp(buf, "SAFECORE ", 9) == 0) {
        char* ip = buf + 9;
        char* sep = strchr(ip, ' ');
        if (sep) {
          *sep = '\0';
          int puerto = atoi(sep + 1);
          if (puerto <= 0 || puerto > 0xFFFF) puerto = 80;
          if (String(ip) != String(CFG.host) || (int)CFG.puerto != puerto) {
            copiaSeg(CFG.host, sizeof(CFG.host), String(ip));
            CFG.puerto = (uint16_t)puerto;
            escribirConfig();
            Serial.print("# HOST auto-descubierto: ");
            Serial.print(ip);
            Serial.print(":");
            Serial.println(puerto);
          }
          origenHost = "auto";
          marcarEnvioOk();
          descubriendo = false;
        }
      }
    }
  }

  if (!descubriendo && fallosSeguidos >= 3 &&
      (ultimoIntentoDescubreMs == 0 ||
       ahora - ultimoIntentoDescubreMs >= MS_REINTENTO_DESCUBRE)) {
    empezarDescubre(ahora);
  }

  if (descubriendo) {
    if (ahora - inicioDescubreMs > MS_VENTANA_DESCUBRE) {
      descubriendo = false;
      return;
    }
    if (ahora - ultimoPktDescubreMs >= MS_PREGUNTA_DESCUBRE) {
      ultimoPktDescubreMs = ahora;
      IPAddress limitada(255, 255, 255, 255);
      IPAddress dirigida = WiFi.localIP();
      dirigida[3] = 255;
      const char* msg = "SAFECORE?";
      udp.beginPacket(dirigida, PUERTO_DESCUBRE);
      udp.write((const uint8_t*)msg, 9);
      udp.endPacket();
      udp.beginPacket(limitada, PUERTO_DESCUBRE);
      udp.write((const uint8_t*)msg, 9);
      udp.endPacket();
    }
  }
}

void consultarEstadoBD(unsigned long ahora) {
  if (ahora - ultimaConsultaBDMs < MS_CONSULTA_BD) return;
  ultimaConsultaBDMs = ahora;
  if (WiFi.status() != WL_CONNECTED) {
    estadoBD = "desconocido";
    return;
  }
  WiFiClient cliente;
  HTTPClient http;
  String url = String("http://") + CFG.host + ":" + CFG.puerto
             + "/api/nodes/" + CFG.serial + "/config";
  http.begin(cliente, url);
  http.setTimeout(5000);
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    if (body.indexOf("\"registrado\":true") >= 0)      estadoBD = "registrado";
    else if (body.indexOf("\"registrado\":false") >= 0) estadoBD = "no-registrado";
    else estadoBD = "desconocido";
  } else {
    estadoBD = "desconocido";
  }
  http.end();
}

void resolverComando(String cmd) {
  String resto;

  if (cmd == "PING") {
    Serial.println("# PONG");
    return;
  }
  if (cmd.startsWith("RATE=")) {
    int s = cmd.substring(5).toInt();
    if (s >= 2 && s <= 300) {
      CFG.rate_s = (uint16_t)s;
      escribirConfig();
      Serial.print("# RATE=");
      Serial.println(CFG.rate_s);
    } else Serial.println("# RATE debe estar entre 2 y 300");
    return;
  }
  if (cmd.startsWith("THR=")) {
    int tvalor = cmd.substring(4).toInt();
    if (tvalor >= 30 && tvalor <= 1023) {
      CFG.umbral = tvalor;
      escribirConfig();
      Serial.print("# THR=");
      Serial.println(CFG.umbral);
    } else Serial.println("# THR debe estar entre 30 y 1023");
    return;
  }
  if (cmd.startsWith("DEVICE=")) {
    resto = cmd.substring(7);
    if (resto.length()) {
      copiaSeg(CFG.serial, sizeof(CFG.serial), resto);
      escribirConfig();
      Serial.print("# DEVICE=");
      Serial.println(CFG.serial);
    }
    return;
  }
  if (cmd.startsWith("FW=")) {
    resto = cmd.substring(3);
    if (resto.length()) {
      copiaSeg(CFG.fw, sizeof(CFG.fw), resto);
      escribirConfig();
      Serial.print("# FW=");
      Serial.println(CFG.fw);
    }
    return;
  }
  if (cmd.startsWith("WIFI=")) {
    resto = cmd.substring(5);
    int pos = resto.indexOf(':');
    String ssid = (pos >= 0) ? resto.substring(0, pos) : resto;
    String pass = (pos >= 0) ? resto.substring(pos + 1) : "";
    if (ssid.length()) {
      copiaSeg(CFG.ssid, sizeof(CFG.ssid), ssid);
      copiaSeg(CFG.password, sizeof(CFG.password), pass);
      escribirConfig();
      aplicarRedNueva(CFG.ssid, CFG.password);
      Serial.println("# WIFI guardado");
    } else Serial.println("# WIFI=ssid:clave");
    return;
  }
  if (cmd.startsWith("HOST=")) {
    resto = cmd.substring(5);
    int pos = resto.indexOf(':');
    if (pos >= 0) {
      copiaSeg(CFG.host, sizeof(CFG.host), resto.substring(0, pos));
      int p = resto.substring(pos + 1).toInt();
      if (p > 0 && p < 65536) CFG.puerto = (uint16_t)p;
    } else {
      copiaSeg(CFG.host, sizeof(CFG.host), resto);
    }
    escribirConfig();
    Serial.print("# HOST=");
    Serial.print(CFG.host);
    Serial.print(":");
    Serial.println(CFG.puerto);
    hostManual();
    return;
  }
  if (cmd.startsWith("RUTA=")) {
    resto = cmd.substring(5);
    if (resto.length() && resto[0] == '/') {
      copiaSeg(CFG.ruta, sizeof(CFG.ruta), resto);
      escribirConfig();
      Serial.print("# RUTA=");
      Serial.println(CFG.ruta);
    } else Serial.println("# RUTA debe empezar con /");
    return;
  }
  if (cmd.startsWith("PIN=")) {
    resto = cmd.substring(4);
    if (resto.length() >= 4 && resto.length() < (int)sizeof(CFG.pin)) {
      copiaSeg(CFG.pin, sizeof(CFG.pin), resto);
      escribirConfig();
      Serial.println("# PIN actualizado");
    } else Serial.println("# PIN: minimo 4 caracteres");
    return;
  }
  if (cmd == "SHOW") {
    Serial.println("# ---------- Config ----------");
    Serial.print("# SSID="); Serial.println(CFG.ssid);
    Serial.print("# PASS="); Serial.println(strlen(CFG.password) ? "(configurada)" : "(vacia)");
    Serial.print("# HOST="); Serial.print(CFG.host);
    Serial.print(":"); Serial.print(CFG.puerto);
    Serial.print(" ("); Serial.print(origenHost); Serial.println(")");
    Serial.print("# RUTA="); Serial.println(CFG.ruta);
    Serial.print("# DEVICE="); Serial.println(CFG.serial);
    Serial.print("# FW="); Serial.println(CFG.fw);
    Serial.print("# THR="); Serial.println(CFG.umbral);
    Serial.print("# RATE="); Serial.println(CFG.rate_s);
    Serial.print("# PIN="); Serial.println(CFG.pin);
    Serial.print("# AP="); Serial.print(nombreAp);
    Serial.print("  portal http://"); Serial.println(WiFi.softAPIP());
    return;
  }
  if (cmd == "FACTORY") {
    restablecerConfig();
    aplicarRedNueva(CFG.ssid, CFG.password);
    Serial.println("# Config de fabrica restaurada");
    return;
  }
  Serial.println("# ? comandos: PING SHOW FACTORY RATE=2..300 THR=30..1023");
  Serial.println("#          DEVICE=name FW=X WIFI=ssid:clave HOST=ip[:puerto]");
  Serial.println("#          RUTA=/x PIN=nuevoPin");
}

void atenderComandos() {
  static char buf[96];
  static byte n = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      buf[n] = '\0';
      String cmd = String(buf);
      cmd.trim();
      if (cmd.length()) resolverComando(cmd);
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MQ2, INPUT);
  pinMode(PIN_ALARMA, OUTPUT);
  digitalWrite(PIN_ALARMA, LOW);

  bool configPrevia = cargarConfig();
  dht.begin();
  delay(2000);
  arranqueMs = millis();

  WiFi.persistent(false);
  WiFi.setAutoReconnect(false);
  WiFi.mode(WIFI_AP_STA);

  if (CFG.ssid[0] != '\0') {
    WiFi.begin(CFG.ssid, CFG.password);
    Serial.print("# WiFi intentando ");
    Serial.println(CFG.ssid);
  }
  lanzarPortal();

  ESP.wdtEnable(8000);

  Serial.println("# -------------------------------------------");
  Serial.print("# SafeCore listo. FW="); Serial.println(CFG.fw);
  Serial.print("# config de EEPROM: ");
  Serial.println(configPrevia ? "si" : "NO, quedaron valores por defecto");
  Serial.print("# PWA:  http://safecore-nodo.local  |  AP: ");
  Serial.print(nombreAp);
  Serial.print("  -> http://"); Serial.println(WiFi.softAPIP());
  Serial.print("# dato -> POST host:puerto");
  Serial.println(CFG.ruta);
  Serial.println("# comandos:PING SHOW FACTORY RATE=10 THR=200 DEVICE=SC-001");
  Serial.println("#          FW=X WIFI=ssid:clave HOST=ip[:p] RUTA=/x PIN=nuevo");
}

void loop() {
  atenderWeb();
  atenderComandos();
  gestionarModoRadio();

  static bool estabaConectado = false;
  bool conectado = (WiFi.status() == WL_CONNECTED);
  if (conectado && !estabaConectado) {
    Serial.print("# WiFi conectado. IP ");
    Serial.println(WiFi.localIP());
    if (!mdnsIniciado) {
      MDNS.begin("safecore-nodo");
      MDNS.addService("http", "tcp", 80);
      mdnsIniciado = true;
      Serial.println("# http://safecore-nodo.local disponible");
    }
    if (fallosSeguidos >= 1) empezarDescubre(millis());
  }
  estabaConectado = conectado;

  unsigned long ahora = millis();
  atenderDescubrimiento();
  consultarEstadoBD(ahora);

  if (ahora - ultimaLectura < (unsigned long)CFG.rate_s * 1000UL) return;
  ultimaLectura = ahora;
  seqTotal++;

  int mq2 = leerMQ2Promedio();

  float t = NAN, h = NAN;
  for (int i = 0; i < 3; i++) {
    t = dht.readTemperature();
    h = dht.readHumidity();
    if (!isnan(t) && !isnan(h)) break;
    delay(200);
  }

  alarmaActiva = (mq2 > CFG.umbral);
  digitalWrite(PIN_ALARMA, alarmaActiva ? HIGH : LOW);

  if (!conectado) {
    Serial.print("# SIN-WIFI seq=");
    Serial.print(seqTotal);
    Serial.print(" gas=");
    Serial.print(mq2);
    Serial.print(" alarm=");
    Serial.println(alarmaActiva ? 1 : 0);
    return;
  }

  String payload = String("{\"device_serial\":\"") + CFG.serial
    + "\",\"device_id\":\"" + WiFi.macAddress()
    + "\",\"fw\":\"" + CFG.fw
    + "\",\"seq\":" + seqTotal
    + ",\"uptime_ms\":" + ahora
    + ",\"readings\":[{\"tipo\":\"gas\",\"valor_crudo\":" + mq2 + "}";
  if (!isnan(t)) {
    payload += ",{\"tipo\":\"temp\",\"valor_crudo\":";
    payload += String(t, 1);
    payload += "}";
  }
  if (!isnan(h)) {
    payload += ",{\"tipo\":\"hum\",\"valor_crudo\":";
    payload += String(h, 1);
    payload += "}";
  }
  payload += "]}";

  if (enviarPorWiFi(payload)) {
    Serial.print("# OK seq=");
    Serial.print(seqTotal);
    Serial.print(" alarm=");
    Serial.println(alarmaActiva ? 1 : 0);
  } else {
    Serial.print("# FALLO envio (descartado) seq=");
    Serial.println(seqTotal);
  }
}
