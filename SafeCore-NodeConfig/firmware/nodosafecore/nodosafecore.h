// nodosafecore.h — cabecera comun de los tres tabs del sketch: Arduino concatena los .ino con el principal primero, asi que aqui se declaran los includes, pines, el tipo de configuracion persistente (NodoConfig, subir CFG_VERSION si cambia su layout), las variables globales compartidas y los prototipos de las funciones de los otros tabs.
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

const uint32_t CFG_MAGIC   = 0x47464353UL;
const uint8_t  CFG_VERSION = 1;

const char* CLAVE_AP = "12345678";

extern DHT dht;
extern NodoConfig CFG;

extern ESP8266WebServer servidor;
extern DNSServer dnsPortal;
extern char nombreAp[];

extern unsigned long ultimaLectura;
extern unsigned long ultimoIntentoWiFi;
extern unsigned long seqTotal;
extern unsigned long arranqueMs;
extern bool ultimoEnvioOk;
extern int  ultimoCodigoHttp;
extern bool alarmaActiva;

extern String origenHost;
extern String estadoBD;

void gestionarModoRadio();

extern const int PIN_MQ2;
extern const int PIN_ALARMA;

void escribirConfig();
bool cargarConfig();
void restablecerConfig();

void atenderWeb();
void lanzarPortal();
void copiaSeg(char* dst, size_t tam, const String& s);
void hostManual();
String escJson(const String& s);

void aplicarRedNueva(const char* ssid, const char* pass);

#endif
