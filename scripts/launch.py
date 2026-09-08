from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kaizen_version import VERSION, BUILD_ID

HOST = "127.0.0.1"
START_PORT = 9550
END_PORT = 9589


def first_free_port() -> int:
    if START_PORT > END_PORT:
        raise RuntimeError(f"Invalid local port range: {START_PORT}-{END_PORT}.")
    for port in range(START_PORT, END_PORT + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free local port found between {START_PORT} and {END_PORT}.")


def open_browser_when_ready(port: int) -> None:
    url = f"http://{HOST}:{port}/"
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.2)
    print(f"[WARN] Server did not become reachable in time. Open {url} manually.")


def main() -> None:
    port = first_free_port()
    url = f"http://{HOST}:{port}/"
    print(f"[START] KAIZEN AI V{VERSION} build {BUILD_ID} will use {url}")
    if port != START_PORT:
        print(f"[INFO] Port {START_PORT} was already in use; selected port {port} instead.")
    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
