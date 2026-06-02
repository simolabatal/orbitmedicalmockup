"""
Custom runserver: lance le bridge COM7 automatiquement au demarrage.
Le bridge doit impérativement se trouver à la racine du projet (BASE_DIR).
"""
import subprocess
import os
import sys
import time
import psutil
from django.core.management.commands.runserver import Command as RunserverCommand


# BASE_DIR = racine du projet (contenant backend/, apps/, bridge_serial.py, ...)
# runserver.py est dans backend/core/management/commands/
# 5 x dirname remonte a la racine du projet.
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )
)

BRIDGE_SCRIPT = os.path.join(BASE_DIR, 'bridge_serial.py')


class Command(RunserverCommand):
    def inner_run(self, *args, **options):
        # --- SECURITE : le bridge DOIT exister à la racine du projet ---
        if not os.path.exists(BRIDGE_SCRIPT):
            print(f'[CRITICAL] Bridge non trouve a la racine : {BRIDGE_SCRIPT}')
            print('[CRITICAL] Arret du serveur. Placez bridge_serial.py à la racine du projet.')
            sys.exit(1)

        # Ne demarrer le bridge que dans le processus SERVEUR reel,
        # pas dans le processus PARENT du reloader auto de Django.
        # Django set RUN_MAIN=true dans le processus enfant.
        use_reloader = options.get('use_reloader', True)
        if use_reloader and os.environ.get('RUN_MAIN') != 'true':
            print('[AUTO-BRIDGE] Processus reloader parent — bridge reporte au processus serveur.')
            super().inner_run(*args, **options)
            return

        # Si un bridge est deja en cours (fichier PID), ne pas en relancer.
        bridge_pid_file = os.path.join(BASE_DIR, 'bridge.pid')
        if os.path.exists(bridge_pid_file):
            try:
                with open(bridge_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    print(f'[AUTO-BRIDGE] Bridge deja actif (PID {pid}) — demarrage saute.')
                    super().inner_run(*args, **options)
                    return
                else:
                    print(f'[AUTO-BRIDGE] Ancien PID {pid} mort — suppression fichier.')
                    os.remove(bridge_pid_file)
            except (ValueError, OSError):
                pass

        bridge = None
        try:
            venv_python = sys.executable
            print(f'[AUTO-BRIDGE] Demarrage du bridge : {BRIDGE_SCRIPT}')
            bridge_out = open(os.path.join(BASE_DIR, 'bridge_out.log'), 'w')
            bridge_err = open(os.path.join(BASE_DIR, 'bridge_err.log'), 'w')
            bridge = subprocess.Popen(
                [venv_python, BRIDGE_SCRIPT],
                stdout=bridge_out,
                stderr=bridge_err,
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            print(f'[AUTO-BRIDGE] Bridge lance (PID {bridge.pid}) avec {venv_python}')
            time.sleep(1)
        except Exception as e:
            print(f'[AUTO-BRIDGE] Echec demarrage bridge : {e}')

        try:
            super().inner_run(*args, **options)
        finally:
            if bridge and bridge.poll() is None:
                print('[AUTO-BRIDGE] Arret du bridge...')
                bridge.terminate()
                bridge.wait(timeout=5)
