"""Demostración local del despliegue PR2 con los tres ejecutables de la práctica."""
import argparse
from contextlib import ExitStack
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


BROKER = ("127.0.0.1", "32002")
NODES = {"127.0.0.2:32001": "réplica 1", "127.0.0.3:32003": "réplica 2"}
BIN = Path(__file__).resolve().parent / "bin"
NAME = "plano.txt"


def emit(message, color=""):
    if color and sys.stdout.isatty():
        message = f"\033[{color}m{message}\033[0m"
    print(message, flush=True)


def wait_until(check, description, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = check()
        if result:
            return result
        time.sleep(0.12)
    raise RuntimeError(f"Sin confirmación de {description}.")


def sockets(flags):
    return subprocess.check_output(["ss", flags], text=True).splitlines()


def client_peer(process):
    for row in sockets("-Htnp"):
        fields = row.split()
        if fields[0] == "ESTAB" and f"pid={process.pid}," in row and fields[4] in NODES:
            return fields[4]
    return None


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if process.stdin:
        process.stdin.close()


def send(process, command):
    process.stdin.write((command + "\n").encode())
    process.stdin.flush()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(automatic):
    links = subprocess.check_output(["ip", "-o", "link", "show"], text=True).splitlines()
    if len(links) != 1 or ": lo:" not in links[0]:
        raise RuntimeError("Inicia la prueba con demo.sh o Probar.cmd.")
    with tempfile.TemporaryDirectory(prefix="gestor-pr2-") as temporary, ExitStack() as stack:
        root = Path(temporary)
        volume = root / "servicio" / "FileManagerDir"
        volume.mkdir(parents=True)
        for directory in ("A", "B", "bin", "logs"):
            (root / directory).mkdir()
        for name in ("brokerFileManager", "serverFileManager", "clientFileManager"):
            binary = root / "bin" / name
            shutil.copyfile(BIN / name, binary)
            binary.chmod(0o700)

        def start(label, name, args, cwd):
            log_path = root / "logs" / label
            log = stack.enter_context(log_path.open("wb"))
            process = subprocess.Popen([str(root / "bin" / name), *args], cwd=cwd,
                                       stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
            stack.callback(stop, process)
            return process

        def listen(port):
            wait_until(lambda: any(row.split()[3].endswith(":" + port) for row in sockets("-Hltn")),
                       f"escucha en el puerto {port}")

        def action(label, command):
            emit(f"{label}  ›  {command}", "1;36")
            if not automatic:
                input()

        start("broker", "brokerFileManager", [], volume.parent)
        listen(BROKER[1])
        for endpoint, label in NODES.items():
            ip, port = endpoint.split(":")
            start(label, "serverFileManager", [*BROKER, ip, port], volume.parent)
            listen(port)

        local = root / "A" / NAME
        local.write_text("Planta baja | Sala 07\nRevision B\n", encoding="utf-8")
        emit("Broker :32002    /    2 servidores en escucha", "1;37")
        emit(f"Origen   {NAME}   ·   {local.stat().st_size} bytes")
        if not automatic:
            emit("Pulsa Intro en cada orden.", "2")
        client_a = start("A", "clientFileManager", BROKER, root / "A")
        peer_a = wait_until(lambda: client_peer(client_a), "la conexión de A")
        emit(f"\nCliente A  →  {NODES[peer_a]}   {peer_a}", "1;34")
        action("A", f"upload {NAME}")
        send(client_a, f"upload {NAME}")
        stored = volume / NAME
        wait_until(lambda: stored.is_file() and stored.read_bytes() == local.read_bytes(),
                   "la escritura en el volumen")
        emit(f"     {stored.stat().st_size} bytes guardados en FileManagerDir/")

        # Las réplicas comunican su carga periódicamente. A mantiene su conexión abierta.
        emit("\nA sigue conectado. Esperando el informe de carga…")
        time.sleep(10.8)
        client_b = start("B", "clientFileManager", BROKER, root / "B")
        peer_b = wait_until(lambda: client_peer(client_b), "la conexión de B")
        if peer_a == peer_b or client_peer(client_a) != peer_a:
            raise RuntimeError("El broker no ha asignado dos conexiones simultáneas a réplicas distintas.")
        emit(f"Cliente B  →  {NODES[peer_b]}   {peer_b}", "1;34")
        action("B", "lls")
        send(client_b, "lls")
        entry = f"FileManagerDir/{NAME}"
        wait_until(lambda: entry in (root / "logs" / "B").read_text(errors="replace").splitlines(),
                   "la respuesta del listado remoto")
        emit("     " + entry)

        action("Volumen", "comparar SHA-256 con el origen")
        original_hash, volume_hash = digest(local), digest(stored)
        if original_hash != volume_hash:
            raise RuntimeError("El contenido del volumen difiere del original.")
        emit("     " + volume_hash)
        emit(f"     Contenido idéntico · {stored.stat().st_size} bytes", "1;32")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto", action="store_true", help="ejecutar los pasos sin pulsar Intro")
    args = parser.parse_args()
    try:
        run(args.auto)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
