"""
Sube a GitHub lo que la app deja listo, de forma opcional (lo invoca Iniciar_App.bat).

Pasos: regenera el sitio cifrado (site/), agrega solo site/ y config/catalogos al commit
(nunca datos ni accesos), hace commit con fecha de Bogota y push.

Salvaguarda: el sitio se cifra con los correos de config/accesos_dashboard.txt y las
contrasenas de data/outputs/control/accesos_dashboard.csv. Si falta alguno de los dos,
publicar generaria contrasenas nuevas y dejaria sin acceso a los usuarios actuales, asi
que en ese caso NO se publica (se informa y se sale sin cambios).

Uso: python scripts/subir_a_git.py             (publica, commit y push)
     python scripts/subir_a_git.py --simular   (muestra que haria, sin tocar nada)
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORREOS = os.path.join(BASE, "config", "accesos_dashboard.txt")
CLAVES = os.path.join(BASE, "data", "outputs", "control", "accesos_dashboard.csv")
RUTAS_GIT = ["site", "config/catalogos"]


def git(*args, check=False):
    r = subprocess.run(["git", *args], cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"[X] git {' '.join(args)} fallo:\n{(r.stderr or r.stdout).strip()}")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true", help="no publica, no hace commit ni push")
    simular = ap.parse_args().simular

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("[!] Esta carpeta no es un repositorio git (o git no esta instalado). No se sube nada.")
        return 0
    faltan = [os.path.relpath(p, BASE) for p in (CORREOS, CLAVES) if not os.path.exists(p)]
    if faltan:
        print("[!] No se publica: faltan " + " y ".join(faltan) + ".")
        print("    Sin ellos se generarian contrasenas nuevas y los usuarios actuales perderian el acceso.")
        print("    Pida esos archivos al equipo tecnico o publique desde el equipo que los tiene.")
        return 0
    if not git("config", "user.name").stdout.strip():
        print("[!] git no tiene usuario configurado (git config user.name / user.email). No se sube nada.")
        return 0

    if simular:
        print("[simulacion] Regeneraria site/, haria commit de", ", ".join(RUTAS_GIT), "y push.")
        print(git("status", "--short", "--", *RUTAS_GIT).stdout or "[simulacion] Sin cambios pendientes ahora.")
        return 0

    print("Regenerando el sitio publicado...")
    r = subprocess.run([sys.executable, os.path.join(BASE, "scripts", "publicar_dashboard.py")], cwd=BASE)
    if r.returncode != 0:
        print("[X] No se pudo regenerar el sitio (revise que 'cryptography' este instalado). No se sube nada.")
        return 1

    git("add", "--", *RUTAS_GIT, check=True)
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("Sin cambios que subir.")
        return 0
    fecha = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M")
    git("commit", "-m", f"Actualizacion de datos del dashboard ({fecha})", check=True)
    p = git("push")
    if p.returncode != 0:
        print("[!] El commit quedo guardado en este equipo, pero el push fallo (probable: hay cambios nuevos en GitHub).")
        print("    Ejecute 'git pull' y luego 'git push', o avise al equipo tecnico.\n" + (p.stderr or p.stdout).strip())
        return 1
    print("Listo: cambios subidos a GitHub. Pages se actualiza en unos minutos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
