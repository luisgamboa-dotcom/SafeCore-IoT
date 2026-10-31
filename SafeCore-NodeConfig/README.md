# README.md

SafeCore NodeConfig es la carpeta aislada del firmware FW 3.0-portal del nodo: el sketch de Arduino (`firmware/nodosafecore/`) que sensa MQ-2/DHT22, expone desde el telefono una PWA para configurar red, servidor, serial, FW, umbral, tasa y PIN sin reflashear (todo persiste en EEPROM), y que se comunica con el servidor FastAPI de `SafeCore-IoT/` por `POST /api/ingest`, con auto-reparacion de IP y sincronizacion de la version de firmware ya aplicadas en el proyecto principal.
