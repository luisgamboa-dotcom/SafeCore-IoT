"""Listener UDP de descubrimiento para nodos SafeCore (FW 3.1+).

El nodo pregunta "SAFECORE?" por UDP broadcast a la red local cuando la IP
del servidor dejo de responder; este listener responde unicast (y por
broadcast) con "SAFECORE <ip> <puerto>" para que el nodo se auto-repare.

Se inicia junto a la app (main.py). Se desactiva con SAFECORE_DISCOVERY=0.
"""
import os
import socket
import threading

PUERTO_DISCOVERY = int(os.getenv("SAFECORE_DISCOVERY_PORT"))
_ACTIVADO = os.getenv("SAFECORE_DISCOVERY") != "0"

_PREGUNTA = b"SAFECORE?"  # lo envia el nodo; solo documentacion
_RESPUESTA_HDR = b"SAFECORE "


def _ip_local():
    """IP de este host en la red por la que saldria al nodo."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _puerto_http():
    """Puerto HTTP donde la app efectivamente sirve: respeta el env/no."""
    return int(os.getenv("PORT"))


def _loop_disco():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", PUERTO_DISCOVERY))
    except OSError as e:
        print(f"[discovery] no se pudo bindear UDP {PUERTO_DISCOVERY}: {e}")
        return
    host = _ip_local()
    puerto = _puerto_http()
    print(f"[discovery] activo en UDP/{PUERTO_DISCOVERY}, "
          f"respondiendo {host}:{puerto}")
    while True:
        try:
            data, addr = sock.recvfrom(256)
            if data.startswith(b"SAFECORE"):
                resp = _RESPUESTA_HDR + f"{host} {puerto}".encode()
                sock.sendto(resp, addr)  # unicast directo al nodo
                sock.sendto(resp, ("255.255.255.255", PUERTO_DISCOVERY))
        except OSError as e:
            print(f"[discovery] error UDP: {e}")


def iniciar_descubrimiento():
    """Arranca el hilo daemon del listener (idempotente)."""
    if not _ACTIVADO:
        print("[discovery] desactivado por SAFECORE_DISCOVERY=0")
        return
    hilo = threading.Thread(target=_loop_disco, name="safecore-discovery",
                            daemon=True)
    hilo.start()
