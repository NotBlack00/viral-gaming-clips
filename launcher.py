from __future__ import annotations

import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
VENV_DIR = APP_DIR / ".venv"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def run_step(command: list[str], label: str) -> None:
    print("\n" + label, flush=True)
    result = subprocess.run(command, cwd=APP_DIR)
    if result.returncode:
        raise RuntimeError(f"{label}: operazione non riuscita (codice {result.returncode}).")


def find_python() -> Path | None:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    candidates = [
        local / "Programs/Python/Python312/python.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Python312/python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    launcher = shutil.which("py")
    if launcher:
        check = subprocess.run([launcher, "-3.12", "-c", "import sys; print(sys.executable)"],
                               capture_output=True, text=True)
        if check.returncode == 0:
            return Path(check.stdout.strip())
    return None


def ensure_python() -> Path:
    python = find_python()
    if python:
        print(f"Python trovato: {python}", flush=True)
        return python

    print("\nPython 3.12 non trovato. Scarico e installo Python automaticamente...", flush=True)
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    installer = APP_DIR / "python-3.12.10-installer.exe"
    urllib.request.urlretrieve(PYTHON_INSTALLER_URL, installer)
    target = local / "Programs/Python/Python312"
    command = [
        str(installer), "/quiet", "InstallAllUsers=0", "Include_launcher=0",
        "Include_pip=1", "Include_test=0", "PrependPath=0", f"TargetDir={target}"
    ]
    result = subprocess.run(command, cwd=APP_DIR)
    installer.unlink(missing_ok=True)
    python = target / "python.exe"
    if result.returncode != 0 or not python.is_file():
        raise RuntimeError("Installazione automatica di Python non riuscita. Riprova o installa Python 3.12 dal sito python.org.")
    return python


def ensure_venv(python: Path) -> Path:
    venv_python = VENV_DIR / "Scripts" / "python.exe"
    if not venv_python.is_file():
        run_step([str(python), "-m", "venv", str(VENV_DIR)], "Creo l'ambiente isolato dell'app...")
    run_step([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
             "Aggiorno il programma di installazione dei componenti...")
    run_step([str(venv_python), "-m", "pip", "install", "-r", str(APP_DIR / "requirements.txt")],
             "Installo/aggiorno i componenti di VIRAL GAMING CLIPS...")
    return venv_python


def ensure_cloudflared() -> Path:
    tools_dir = APP_DIR / "tools"
    tools_dir.mkdir(exist_ok=True)
    executable = tools_dir / "cloudflared.exe"
    if not executable.is_file():
        print("\nScarico il componente gratuito per il collegamento remoto sicuro...", flush=True)
        urllib.request.urlretrieve(CLOUDFLARED_URL, executable)
    return executable


def wait_for_server(process: subprocess.Popen, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Il motore dell'app si è chiuso durante l'avvio. Leggi gli errori qui sopra.")
        try:
            with socket.create_connection(("127.0.0.1", 8501), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError("L'app non ha risposto entro 2 minuti. Controlla gli errori mostrati sopra.")


def tunnel_reader(process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print("[COLLEGAMENTO] " + line.rstrip(), flush=True)
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line, re.I)
        if match:
            print("\n" + "=" * 64, flush=True)
            print("LINK DA APRIRE SUL TABLET/ALTRO PC:", flush=True)
            print(match.group(0), flush=True)
            print("PASSWORD TEMPORANEA:", os.environ["VGC_ACCESS_PASSWORD"], flush=True)
            print("=" * 64 + "\n", flush=True)


def main() -> int:
    if os.name != "nt":
        print("Questa versione è destinata a Windows 10/11.")
        input("Premi Invio per chiudere...")
        return 1

    server = None
    tunnel = None
    try:
        print("=" * 64)
        print("       VIRAL GAMING CLIPS - AVVIO WINDOWS")
        print("=" * 64)
        python = ensure_python()
        venv_python = ensure_venv(python)
        cloudflared = ensure_cloudflared()

        password = secrets.token_urlsafe(16)
        os.environ["VGC_ACCESS_PASSWORD"] = password

        print("\nAvvio del motore video sul PC...", flush=True)
        server = subprocess.Popen(
            [str(venv_python), "-m", "streamlit", "run", str(APP_DIR / "app.py"),
             "--server.address", "127.0.0.1", "--server.port", "8501",
             "--server.headless", "true", "--server.maxUploadSize", "4096",
             "--server.maxMessageSize", "4096"],
            cwd=APP_DIR, env=os.environ.copy()
        )
        wait_for_server(server)

        print("\nCreo il collegamento Internet temporaneo...", flush=True)
        tunnel = subprocess.Popen(
            [str(cloudflared), "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8501"],
            cwd=APP_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1
        )
        threading.Thread(target=tunnel_reader, args=(tunnel,), daemon=True).start()

        print("\nL'app è in esecuzione. Non chiudere questa finestra.", flush=True)
        print("Quando compare il link, invialo privatamente insieme alla password.", flush=True)
        print("Per terminare il collegamento e spegnere l'app, premi CTRL+C.", flush=True)
        while server.poll() is None and tunnel.poll() is None:
            time.sleep(1)
        return 0
    except KeyboardInterrupt:
        print("\nChiusura richiesta...", flush=True)
        return 0
    except Exception as exc:
        print(f"\nERRORE: {exc}", flush=True)
        return 1
    finally:
        for process in (tunnel, server):
            if process and process.poll() is None:
                process.terminate()
        input("\nPremi Invio per chiudere questa finestra...")


if __name__ == "__main__":
    raise SystemExit(main())
