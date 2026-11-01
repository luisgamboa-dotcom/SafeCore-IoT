// configStore.ino — configuracion persistente en EEPROM del nodo SafeCore (FW 3.0-portal): define el bloque CFG con checksum CRC8, sus valores por defecto heredados del FW v2.1 (red, servidor, serial, umbral, tasa y PIN) y las funciones de escritura, carga con validacion y restablecimiento; los tipos e includes comunes viven en nodosafecore.h.
#include "nodosafecore.h"

DHT dht(DHTPIN, DHTTYPE);

const int PIN_MQ2 = A0;
const int PIN_ALARMA = D8;

NodoConfig CFG;

NodoConfig configPorDefecto() {
  NodoConfig c;
  memset(&c, 0, sizeof(c));
  c.magic = CFG_MAGIC;
  c.version = CFG_VERSION;
  strncpy(c.ssid, "POCO", sizeof(c.ssid) - 1);
  strncpy(c.password, "luis200812", sizeof(c.password) - 1);
  strncpy(c.host, "10.115.20.30", sizeof(c.host) - 1);
  c.puerto = 8000;
  strncpy(c.ruta, "/api/ingest", sizeof(c.ruta) - 1);
  strncpy(c.serial, "SC-001", sizeof(c.serial) - 1);
  strncpy(c.fw, "3.1-auto", sizeof(c.fw) - 1);
  c.umbral = 200;
  c.rate_s = 10;
  strncpy(c.pin, "1234", sizeof(c.pin) - 1);
  c.crc = 0;
  return c;
}

uint8_t crc8Config(const NodoConfig& c) {
  const uint8_t* p = (const uint8_t*)&c;
  size_t n = sizeof(NodoConfig) - 1;
  uint8_t crc = 0;
  while (n--) {
    uint8_t x = *p++;
    for (uint8_t i = 0; i < 8; i++) {
      uint8_t mezcla = (crc ^ x) & 1;
      crc >>= 1;
      x >>= 1;
      if (mezcla) crc ^= 0x8C;
    }
  }
  return crc;
}

void escribirConfig() {
  CFG.crc = crc8Config(CFG);
  EEPROM.put(0, CFG);
  EEPROM.commit();
}

void restablecerConfig() {
  CFG = configPorDefecto();
  escribirConfig();
}

bool cargarConfig() {
  EEPROM.begin(sizeof(NodoConfig) + 16);
  NodoConfig c;
  EEPROM.get(0, c);
  bool ok = (c.magic == CFG_MAGIC && c.version == CFG_VERSION &&
             c.crc == crc8Config(c));
  if (ok) {
    CFG = c;
  } else {
    CFG = configPorDefecto();
    escribirConfig();
  }
  CFG.ssid[sizeof(CFG.ssid) - 1] = '\0';
  CFG.password[sizeof(CFG.password) - 1] = '\0';
  CFG.host[sizeof(CFG.host) - 1] = '\0';
  CFG.ruta[sizeof(CFG.ruta) - 1] = '\0';
  CFG.serial[sizeof(CFG.serial) - 1] = '\0';
  CFG.fw[sizeof(CFG.fw) - 1] = '\0';
  CFG.pin[sizeof(CFG.pin) - 1] = '\0';
  return ok;
}
