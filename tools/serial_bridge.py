"""Puente USB -> REST para testeo SafeCore IoT.

Lee el JSON del Arduino por USB, mapea LAS 3 magnitudes (gas ADC crudo +
temperatura + humedad) y hace POST a FastAPI. El ADC se envia CRUDO:
Python NO convierte a ppm (decision del equipo).

Uso:
    pip install pyserial requests
    python tools/serial_bridge.py --port COM5 --api http://localhost:8000/api/ingest
    python tools/serial_bridge.py --port /dev/ttyUSB0 --api http://localhost:8000/api/ingest

Si FastAPI esta caido, guarda lineas en buffer.jsonl y las reenvia despues.
"""
import argparse
import json
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    sys.exit("Falta pyserial: pip install pyserial")

try:
    import requests
except ImportError:
    sys.exit("Falta requests: pip install requests")

BUFFER = Path(__file__).with_name("buffer.jsonl")


def parse_linea(linea):
    """Convierte una linea del Arduino en payload REST. Retorna dict o None."""
    linea = linea.strip()
    if not linea or not linea.startswith("{"):
        return None  # ignora debug '# ...' y recuadros viejos
    try:
        d = json.loads(linea)
    except json.JSONDecodeError:
        return None
    for k in ("device", "seq", "mq2_adc"):
        if k not in d:
            return None
    readings = [{"tipo": "gas", "valor_crudo": float(d["mq2_adc"])}]
    if d.get("temp_c") is not None:  # null cuando el DHT22 falla -> se omite
        readings.append({"tipo": "temp", "valor_crudo": float(d["temp_c"])})
    if d.get("hum_pct") is not None:
        readings.append({"tipo": "hum", "valor_crudo": float(d["hum_pct"])})
    return {
        "device_serial": d.get("device_override") or d["device"],
        "fw": d.get("fw"),
        "seq": int(d["seq"]),
        "uptime_ms": d.get("uptime_ms"),
        "readings": readings,
    }


def enviar(api, payload, timeout=5):
    r = requests.post(api, json=payload, timeout=timeout)
    return r.status_code, r.text


def guardar_buffer(payload):
    with open(BUFFER, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def reenviar_buffer(api):
    if not BUFFER.exists():
        return 0
    pendientes = BUFFER.read_text(encoding="utf-8").splitlines()
    ok, resto = 0, []
    for linea in pendientes:
        try:
            _, _ = enviar(api, json.loads(linea))
            ok += 1
        except Exception:
            resto.append(linea)
    BUFFER.write_text("\n".join(resto) + ("\n" if resto else ""), encoding="utf-8")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Puente USB->REST SafeCore (testeo)")
    ap.add_argument("--port", required=True, help="COM5 o /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--api", default="http://localhost:8000/api/ingest")
    ap.add_argument("--device", default=None, help="Sobrescribe el serial del JSON")
    args = ap.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=2)
    time.sleep(2)  # el Wemos se reinicia al abrir el puerto
    print(f"Escuchando {args.port} -> {args.api} (Ctrl+C para salir)")
    reenviadas = reenviar_buffer(args.api)
    if reenviadas:
        print(f"Reenviadas del buffer: {reenviadas}")

    while True:
        cruda = ser.readline().decode("utf-8", errors="replace")
        if not cruda.strip():
            continue
        payload = parse_linea(cruda)
        if payload is None:
            print(f"IGNORADA: {cruda.strip()[:80]}")
            continue
        if args.device:
            payload["device_serial"] = args.device
        try:
            code, body = enviar(args.api, payload)
            print(f"seq={payload['seq']} -> HTTP {code} {body[:120]}")
        except Exception as e:
            guardar_buffer(payload)
            print(f"seq={payload['seq']} -> API caida, guardada en buffer ({e})")


if __name__ == "__main__":
    main()
