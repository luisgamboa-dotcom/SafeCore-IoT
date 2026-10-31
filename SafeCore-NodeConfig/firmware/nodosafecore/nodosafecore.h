// nodosafecore.h — cabecera comun de los tres tabs del sketch
// Arduino concatena los .ino con el PRINCIPAL (nodosafecore.ino) PRIMERO,
// por eso las referencias cruzadas (CFG, servidor, dht, funciones de otros
// tabs) se declaran aca y los .h guardan el orden sin importar la
// concatenacion. Cada tab incluye esta cabecera con un guard.

#ifndef NODO_SAFECORE_H
#define NODO_SAFECORE_H

#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <DNSServer.h>
#include <WiFiUdp.h>
#include <EEPROM.h>
#include <WiFiClient.h>

#define DHTPIN D4
#define DHTTYPE DHT22

// ---------- tipo de configuracion persistente (EEPROM emulada) ----------
// Si cambiara el layout: subir CFG_VERSION.
struct NodoConfig {
  uint32_t magic;
  uint8_t  version;
  char     ssid[33];
  char     password[65];
  char     host[64];
  uint16_t puerto;
  char     ruta[24];
  char     serial[16];
  char     fw[24];
  int      umbral;
  uint16_t rate_s;
  char     pin[9];
  uint8_t  crc;
};

const uint32_t CFG_MAGIC   = 0x47464353UL;  // 'SCFG' en little-endian
const uint8_t  CFG_VERSION = 1;

const char* CLAVE_AP = "12345678";

// ---------- globals definidos en los otros tabs ----------
extern DHT dht;                 // (configStore.ino)
extern NodoConfig CFG;          // (configStore.ino)

extern ESP8266WebServer servidor;  // (webPortal.ino)
extern DNSServer dnsPortal;        // (webPortal.ino)
extern char nombreAp[];            // (webPortal.ino) "SafeCore-XXXX"

// runtime compartido con el loop (webPortal.ino los define)
extern unsigned long ultimaLectura;
extern unsigned long ultimoIntentoWiFi;
extern unsigned long seqTotal;
extern unsigned long arranqueMs;
extern bool ultimoEnvioOk;
extern int  ultimoCodigoHttp;
extern bool alarmaActiva;

// origen de la IP del servidor / estado de la BD (se actualizan en nodosafecore.ino)
extern String origenHost;   // "auto" | "manual"
extern String estadoBD;     // "registrado" | "no-registrado" | "desconocido"

// FW 3.1.2: maquina de radio AP/STA (definida en nodosafecore.ino)
void gestionarModoRadio();

// pines fisicos (v2.1: MQ-2 en ADC, alarma LED/buzzer en D8)
extern const int PIN_MQ2;
extern const int PIN_ALARMA;

// ---------- prototipos ----------
// configStore.ino
void escribirConfig();
bool cargarConfig();
void restablecerConfig();

// webPortal.ino
void atenderWeb();
void lanzarPortal();
void copiaSeg(char* dst, size_t tam, const String& s);
void hostManual();
String escJson(const String& s);

// nodosafecore.ino
void aplicarRedNueva(const char* ssid, const char* pass);

#endif  // NODO_SAFECORE_H
