// SafeCore IoT - Nodo WiFi (Wemos D1 + MQ-2 + DHT22)
// Modo WiFi: envia las lecturas por HTTP POST directo a FastAPI.
// El USB queda SOLO como fuente de alimentacion (y monitor debug);
// los datos viajan por WiFi, ya no por el puerto serie.
// El Arduino manda ADC CRUDO; FastAPI califica y guarda.
//
// Endpoint: POST http://SERVIDOR:8000/api/ingest
// Payload: {"device_serial":"SC-001","fw":"2.0-wifi","seq":42,
//           "uptime_ms":12345,"readings":[{"tipo":"gas","valor_crudo":512}, ...]}
// Comandos por Monitor Serie: PING | RATE=10 | THR=200 | DEVICE=SC-001

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
const char* FW_VERSION = "2.0-wifi";

// ---------- Configuracion de conexion WiFi ----------
// SSID y clave viven en secrets.h (no versionado). El servidor es el PC
// donde corre FastAPI: usa su IP de la red WiFi (NO localhost/127.0.0.1,
// esa solo existe dentro del PC).
const char* SERVIDOR_HOST = "192.168.1.16";  // IP actual del PC en WiFi, puede cambiar
const int SERVIDOR_PUERTO = 8000;
const char* API_RUTA = "/api/ingest";

char DEVICE_SERIAL[16] = "SC-001";  // cambiable con DEVICE=xxx
int UMBRAL_ALARMA = 200;            // solo flag local, Python decide
unsigned long INTERVALO_MS = 10000; // cada 10 s (cambiable con RATE=s)
const int MUESTRAS_MQ2 = 5;         // promedio de 5 para estabilizar

// ---------- Estado ----------
unsigned long ultimaLectura = 0;
unsigned long seq = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MQ2, INPUT);
  dht.begin();
  delay(2000);  // estabilizacion MQ-2 / DHT22
  conectarWiFi();
  Serial.println("# SafeCore listo. Datos por WiFi. Comandos: PING RATE=10 THR=200 DEVICE=SC-001");
}

// Conecta a la WiFi configurada arriba. El USB solo alimenta el nodo.
void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("# Conectando a WiFi ");
  Serial.print(WIFI_SSID);
  Serial.print(" ");
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 40) {  // ~20 s maximo
    delay(500);
    Serial.print(".");
    intentos++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("# WiFi OK. IP del nodo: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("# WiFi FALLO: revisa SSID/clave. Reintenta en el loop.");
  }
}

// Envia una lectura a FastAPI por HTTP POST. Retorna true si el servidor la acepto.
bool enviarPorWiFi(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) {
    conectarWiFi();
    if (WiFi.status() != WL_CONNECTED) return false;
  }
  WiFiClient cliente;
  HTTPClient http;
  String url = String("http://") + SERVIDOR_HOST + ":" + SERVIDOR_PUERTO + API_RUTA;
  http.begin(cliente, url);
  http.addHeader("Content-Type", "application/json");
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

// Lee comandos simples sin bloquear el loop (hasta fin de linea)
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
    delay(500);
  }
  int alarm = (mq2 > UMBRAL_ALARMA) ? 1 : 0;

  // Payload directo para POST /api/ingest (mismo formato que espera FastAPI).
  // Las magnitudes nulas (DHT22 fallando) se omiten, igual que hacia el puente USB.
  String payload = String("{\"device_serial\":\"") + DEVICE_SERIAL
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

  // Via de datos: WiFi. El USB solo alimenta y muestra este debug.
  if (enviarPorWiFi(payload)) {
    Serial.print("# OK seq=");
    Serial.print(seq);
    Serial.print(" alarm=");
    Serial.println(alarm);
  } else {
    Serial.print("# FALLO envio seq=");
    Serial.println(seq);
  }
}
