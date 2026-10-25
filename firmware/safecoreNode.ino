// SafeCore IoT - Nodo WiFi (Wemos D1 + MQ-2 + DHT22) FW 2.1-autonomo
// Modo en vivo SIN guardar: sensa, envia por HTTP POST y descarta.
// - Sin WiFi o sin servidor: sigue sensando, activa alarma local y descarta
//   el paquete (sin cola, sin EEPROM/SD). No depende del PC ni del USB:
//   el USB es solo alimentacion; con fuente externa funciona igual.
// - El servidor tampoco guarda (modo en-vivo-sin-guardar, solo memoria).
//
// Endpoint: POST http://SERVIDOR:8000/api/ingest
// Payload: {"device_serial":"SC-001","device_id":"40:91:51:52:89:38","fw":"2.1-autonomo",
//           "seq":42,"uptime_ms":12345,"readings":[{"tipo":"gas","valor_crudo":512}, ...]}
// Comandos por Monitor Serie (opcionales): PING | RATE=10 | THR=200 | DEVICE=SC-001

#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include "secrets.h"  // WIFI_SSID y WIFI_PASSWORD (no versionado, ver .gitignore)

// ---------- Configuracion ----------
#define DHTPIN D4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int PIN_MQ2 = A0;
const int PIN_ALARMA = D8;  // LED/buzzer local: funciona sin WiFi ni servidor
const char* FW_VERSION = "2.1-autonomo";

// ---------- Configuracion de conexion WiFi ----------
// SSID y clave viven en secrets.h. El servidor es el PC donde corre FastAPI:
// usa su IP de la red WiFi actual (NO localhost/127.0.0.1).
// Red actual (hotspot POCO): PC = 10.110.143.30. Si el hotspot se reinicia
// y la IP cambia, actualiza solo esta linea y reflashea.
const char* SERVIDOR_HOST = "10.115.20.30";
const int SERVIDOR_PUERTO = 8000;
const char* API_RUTA = "/api/ingest";

char DEVICE_SERIAL[16] = "SC-001";  // cambiable con DEVICE=xxx
int UMBRAL_ALARMA = 200;            // alarma local aunque no haya servidor
unsigned long INTERVALO_MS = 10000; // cada 10 s (cambiable con RATE=s)
const int MUESTRAS_MQ2 = 5;         // promedio de 5 para estabilizar
const unsigned long REINTENTO_WIFI_MS = 10000;  // reintento no bloqueante

// ---------- Estado ----------
unsigned long ultimaLectura = 0;
unsigned long ultimoIntentoWiFi = 0;
unsigned long seq = 0;

void intentarWiFi(bool forzar) {
  if (WiFi.status() == WL_CONNECTED) return;
  unsigned long ahora = millis();
  if (!forzar && ahora - ultimoIntentoWiFi < REINTENTO_WIFI_MS) return;
  ultimoIntentoWiFi = ahora;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("# WiFi intentando ");
  Serial.println(WIFI_SSID);
}

void setup() {
  Serial.begin(115200);  // opcional: sin USB igual funciona con fuente externa
  pinMode(PIN_MQ2, INPUT);
  pinMode(PIN_ALARMA, OUTPUT);
  digitalWrite(PIN_ALARMA, LOW);
  dht.begin();
  delay(2000);  // estabilizacion MQ-2 / DHT22
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  intentarWiFi(true);
  Serial.println("# SafeCore listo. En vivo sin guardar. Comandos: PING RATE=10 THR=200 DEVICE=SC-001");
}

// Envia una lectura a FastAPI por HTTP POST. Retorna true si el servidor la acepto.
// Si no hay WiFi o falla el POST, retorna false y el llamador DESCARTA (no guarda).
bool enviarPorWiFi(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) return false;
  WiFiClient cliente;
  HTTPClient http;
  String url = String("http://") + SERVIDOR_HOST + ":" + SERVIDOR_PUERTO + API_RUTA;
  http.begin(cliente, url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);
  int codigo = http.POST(payload);
  http.end();
  return (codigo >= 200 && codigo < 300);
}

int leerMQ2Promedio() {
  long suma = 0;
  for (int i = 0; i < MUESTRAS_MQ2; i++) {
    suma += analogRead(PIN_MQ2);
    delay(20);
  }
  return (int)(suma / MUESTRAS_MQ2);
}

// Lee comandos simples sin bloquear el loop (hasta fin de linea). Opcional.
void atenderComandos() {
  static char buf[32];
  static byte n = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      buf[n] = '\0';
      if (strncmp(buf, "PING", 4) == 0) {
        Serial.println("# PONG");
      } else if (strncmp(buf, "RATE=", 5) == 0) {
        int s = atoi(buf + 5);
        if (s >= 2 && s <= 300) {
          INTERVALO_MS = (unsigned long)s * 1000UL;
          Serial.print("# RATE=");
          Serial.println(s);
        }
      } else if (strncmp(buf, "THR=", 4) == 0) {
        UMBRAL_ALARMA = atoi(buf + 4);
        Serial.print("# THR=");
        Serial.println(UMBRAL_ALARMA);
      } else if (strncmp(buf, "DEVICE=", 7) == 0) {
        strncpy(DEVICE_SERIAL, buf + 7, sizeof(DEVICE_SERIAL) - 1);
        DEVICE_SERIAL[sizeof(DEVICE_SERIAL) - 1] = '\0';
        Serial.print("# DEVICE=");
        Serial.println(DEVICE_SERIAL);
      }
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
}

void loop() {
  atenderComandos();
  intentarWiFi(false);  // no bloquea el sensado

  unsigned long ahora = millis();
  if (ahora - ultimaLectura < INTERVALO_MS) return;
  ultimaLectura = ahora;
  seq++;

  int mq2 = leerMQ2Promedio();

  // DHT22 con 3 reintentos (puede fallar 1 de cada tanto)
  float t = NAN, h = NAN;
  for (int i = 0; i < 3; i++) {
    t = dht.readTemperature();
    h = dht.readHumidity();
    if (!isnan(t) && !isnan(h)) break;
    delay(200);
  }
  // Alarma LOCAL: no depende del servidor ni del WiFi.
  int alarm = (mq2 > UMBRAL_ALARMA) ? 1 : 0;
  digitalWrite(PIN_ALARMA, alarm ? HIGH : LOW);

  String payload = String("{\"device_serial\":\"") + DEVICE_SERIAL
    + "\",\"device_id\":\"" + WiFi.macAddress()
    + "\",\"fw\":\"" + FW_VERSION
    + "\",\"seq\":" + seq
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

  // Via de datos: WiFi. Sin conexion se DESCARTA (sin guardar) y se sigue.
  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("# SIN-WIFI seq=");
    Serial.print(seq);
    Serial.print(" gas=");
    Serial.print(mq2);
    Serial.print(" alarm=");
    Serial.println(alarm);
    return;
  }
  if (enviarPorWiFi(payload)) {
    Serial.print("# OK seq=");
    Serial.print(seq);
    Serial.print(" alarm=");
    Serial.println(alarm);
  } else {
    Serial.print("# FALLO envio (descartado) seq=");
    Serial.println(seq);
  }
}
