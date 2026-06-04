#!/usr/bin/env python
"""
L'Fellah Bridge Serial v7 — Arduino COM7 → API Django (iot) + Fallback SQLite
Bufferisation intelligente ligne-par-ligne.
URL d'ingestion: /api/iot/sensor-ingest/

En cas d'indisponibilite de l'API (MySQL/XAMPP eteint), ecrit directement
dans la base SQLite (backup) via Django ORM pour ne perdre aucune donnee.

⚠️  CONSIGNE DE SECURITE :
    Fermez le Serial Monitor de l'IDE Arduino avant de lancer ce bridge,
    sinon le port COM7 reste verrouille et les donnees ne passent pas.

Usage : python bridge_serial.py
"""

import json
import time
import sys
import os
import logging

logger = logging.getLogger(__name__)

try:
    import serial
except ImportError:
    print("pip install pyserial")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

try:
    import psutil
    PSUTIL = True
except ImportError:
    psutil = None
    PSUTIL = False

# Django ORM pour fallback SQLite
DJANGO_AVAILABLE = False
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lfellah_server.settings.dev')
    import django
    django.setup()
    from iot.models import Device, SensorData
    DJANGO_AVAILABLE = True
    print('[BRIDGE] Django ORM charge — fallback SQLite actif')
except Exception as e:
    print(f'[BRIDGE] Django ORM indisponible : {e}')
    print('[BRIDGE] Le fallback SQLite ne sera pas utilise')

# ─── CONFIG ─────────────────────────────────────────────────────
SERIAL_PORT  = 'COM7'
BAUDRATE     = 9600
DEVICE_TOKEN = 'abcd1234sensor01'
API_URL      = 'http://127.0.0.1:8000/api/iot/sensor-ingest/'
SYNC_URL     = 'http://127.0.0.1:8000/api/iot/sync-now/'
RETRY_DELAY  = 5
MAX_LINE_LEN = 1024
BRIDGE_PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bridge.pid')
# ──────────────────────────────────────────────────────────────────

sent_ok        = 0
sent_err       = 0
line_buf       = ""
mysql_was_down = False  # tracker de l'etat MySQL pour la re-synchronisation automatique

# Chars Arduino
STX = '\x02'
ETX = '\x03'
START_JSON = '{'
END_JSON   = '}'


def _force_free_com7():
    """
    Tue tout processus qui verrouille COM7 (IDE Arduino, moniteurs serie,
    anciennes instances Python). Retourne la liste des noms des processus
    tues pour affichage dans les logs critiques.
    """
    if not PSUTIL:
        return []
    my_pid = os.getpid()
    print(f'[CLEANUP] Scan processus verrouillant COM7 (moi=PID {my_pid})')
    killed_names = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid == my_pid:
                print(f'[CLEANUP] Skip moi-meme (PID {pid})')
                continue
            name = proc.info['name'] or 'Unknown'
            name_lower = name.lower()
            cmd = ' '.join(proc.info['cmdline'] or [])

            # Ne jamais tuer le serveur Django (runserver/manage.py)
            if 'manage.py' in cmd or 'runserver' in cmd:
                print(f'[CLEANUP] Skip serveur Django PID {pid}')
                continue

            # Ne jamais tuer le processus parent qui nous a spawn (son cmdline contient bridge_serial.py)
            if 'bridge_serial.py' in cmd:
                continue

            should_kill = False
            reason = ''
            # 1. Cibles connues : Arduino IDE, Serial Monitor, Python avec COM7
            known_targets = ['arduino', 'javaw', 'java', 'serial', 'putty', 'tera term', 'minicom']
            if any(t in name_lower for t in known_targets):
                should_kill = True
                reason = 'nom connu'
            if 'python' in name_lower and 'COM7' in cmd:
                should_kill = True
                reason = 'cmdline COM7'
            # 2. Verifier les handles ouverts (Windows) — le veritable verrou
            try:
                for item in proc.open_files():
                    if 'COM7' in item.path.upper():
                        should_kill = True
                        reason = 'handle COM7 ouvert'
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            if should_kill:
                print(f'[CLEANUP] Terminaison PID {pid} ({name}) — {reason}')
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except psutil.TimeoutExpired:
                    print(f'[CLEANUP] Kill force PID {pid} ({name})')
                    proc.kill()
                    proc.wait(timeout=1)
                killed_names.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed_names:
        print(f'[CLEANUP] {len(killed_names)} processus liberes: {killed_names}. Tentative connexion COM7...')
        time.sleep(1.5)
    return killed_names


def parse_complete_json(buf):
    """
    Extrait le premier JSON complet du buffer en cherchant les accolades equilibrees.
    Retourne (dict, reste_buffer) ou (None, buf) si incomplet.
    Gere le cas ou { et } sont sur des lignes separees (pretty-printed Arduino).
    """
    buf = buf.strip()
    if not buf:
        return None, ""

    start = buf.find(START_JSON)
    if start == -1:
        return None, ""

    json_candidate = buf[start:]
    depth = 0
    end = -1
    for i, ch in enumerate(json_candidate):
        if ch == START_JSON:
            depth += 1
        elif ch == END_JSON:
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        # JSON incomplet — on garde tout le candidat pour la prochaine iteration
        return None, json_candidate

    json_str = json_candidate[:end + 1]
    try:
        data = json.loads(json_str)
        remaining = buf[:start] + json_candidate[end + 1:]
        return data, remaining
    except json.JSONDecodeError as e:
        print(f"[PARSE] JSON invalide: {e} | buf: {json_str[:80]}")
        remaining = buf[:start] + json_candidate[end + 1:]
        return None, remaining


def extract_json_from_line(line):
    """
    Extrait un JSON d'une ligne qui peut contenir du bruit avant/apres.
    Ex: ">>> {"temp":25.3,...}" <<<" ou juste "{"temp":25.3}"
    """
    line = line.strip()
    start = line.find(START_JSON)
    if start == -1:
        return None

    end = line.rfind(END_JSON)
    if end == -1 or end < start:
        return None

    json_str = line[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def send(data):
    global sent_ok, sent_err

    # Validation croisee : affiche la structure exacte du JSON reçu de l'Arduino
    print(f'[BRIDGE] DEBUG: Parsed JSON: {data}')
    print(f'[BRIDGE] TYPE   : t={type(data.get("temp")).__name__} h={type(data.get("hum")).__name__} tds={type(data.get("tds")).__name__} ph={type(data.get("ph")).__name__}')

    # Mapping Arduino keys → API keys (couvre les deux conventions)
    payload = {
        'device_token': DEVICE_TOKEN,
        'temperature':   _map_value(data, 'temperature', 'temp', 'Temperature', 'T'),
        'humidity':      _map_value(data, 'humidity', 'hum', 'Humidity', 'H'),
        'tds':           _map_value(data, 'tds', 'TDS'),
        'ph':            _map_value(data, 'ph', 'pH', 'PH'),
        'ph_raw':        _map_value(data, 'ph_raw', 'phRaw', 'ph_raw', 'pH_raw'),
        'soil_moisture': _map_value(data, 'soil_moisture', 'soil', 'soil_moisture', 'Soil'),
        'relay':         data.get('relay', 'OFF'),
        'mode':          data.get('mode', 'AUTO'),
    }

    if all(v is None for k, v in payload.items() if k != 'device_token'):
        print(f"[BRIDGE] SKIP - toutes valeurs nulles apres mapping: {data}")
        return False

    print(f'[BRIDGE] Mapping     : temp={payload["temperature"]} hum={payload["humidity"]} tds={payload["tds"]} ph={payload["ph"]}')
    payload_str = json.dumps(payload)
    print(f'[BRIDGE] Payload construit pour POST : {payload_str}')
    try:
        r = requests.post(API_URL, json=payload, timeout=10)
        print(f'[BRIDGE] Envoi vers Django : {r.status_code}')
        if r.status_code == 201:
            sent_ok += 1
            try:
                resp_body = r.json()
                print(f'[BRIDGE] Reponse API : {resp_body}')
            except Exception:
                print(f'[BRIDGE] Reponse brute : {r.text[:200]}')
            print(f'[BRIDGE] Données envoyées avec succès : {r.status_code}')
            _auto_sync_check()  # Verifier si MySQL vient de revenir en ligne
            return True
        else:
            sent_err += 1
            print(f'[BRIDGE] ERR #{sent_err} | {payload_str} | HTTP {r.status_code} | {r.text[:120]}')
            return False
    except requests.exceptions.ConnectionError:
        sent_err += 1
        print(f'[BRIDGE] CONN REFUSED | {payload_str}')
        _fallback_sqlite(payload)
    except Exception as e:
        sent_err += 1
        print(f'[BRIDGE] EXCEPTION | {payload_str} | {type(e).__name__}: {e}')
        _fallback_sqlite(payload)
    return False


def _fallback_sqlite(payload):
    """Ecriture directe dans SQLite (default) quand l'API est injoignable."""
    global mysql_was_down
    mysql_was_down = True  # Marque que MySQL est tombe

    if not DJANGO_AVAILABLE:
        print('[WARNING] MySQL/API indisponible ET Django ORM non charge. Donnees PERDUES.')
        return

    try:
        device = Device.objects.using('default').filter(device_token=DEVICE_TOKEN, is_active=True).first()
        if not device:
            print(f'[FALLBACK] Device inconnu: {DEVICE_TOKEN}')
            return
        sd = SensorData.objects.using('default').create(
            device=device,
            temperature=payload.get('temperature'),
            humidity=payload.get('humidity'),
            tds=payload.get('tds'),
            ph=payload.get('ph'),
        )
        print(f'[WARNING] MySQL indisponible, ecriture dans le buffer SQLite (default) id={sd.id}')
    except Exception as e:
        print(f'[FALLBACK] Echec ecriture SQLite : {type(e).__name__}: {e}')


def _auto_sync_check():
    """
    Verifie si MySQL est revenu en ligne apres une panne.
    Si oui, declenche la re-synchronisation automatique SQLite → MySQL.
    """
    global mysql_was_down
    if not mysql_was_down:
        return  # MySQL etait deja en ligne, rien a faire

    # Tester si MySQL est de nouveau disponible en appellant sync-now
    try:
        r = requests.post(SYNC_URL, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'ok' and data.get('synced', 0) > 0:
                print(f'[AUTO-SYNC] MySQL retabli ! {data["synced"]} enregistrements synchronises SQLite → MySQL.')
                mysql_was_down = False
            elif data.get('status') == 'ok':
                print('[AUTO-SYNC] MySQL retabli ! Buffer SQLite vide, rien a synchroniser.')
                mysql_was_down = False
            elif data.get('status') == 'skipped':
                print('[AUTO-SYNC] MySQL toujours indisponible — nouvelle tentative au prochain cycle.')
            else:
                print(f'[AUTO-SYNC] Reponse inattendue : {data}')
        else:
            print(f'[AUTO-SYNC] Echec sync-now HTTP {r.status_code}')
    except requests.exceptions.ConnectionError:
        print('[AUTO-SYNC] API sync-now injoignable')
    except Exception as e:
        print(f'[AUTO-SYNC] Erreur : {type(e).__name__}: {e}')


def _find_com7_blockers():
    """Retourne la liste des noms des processus qui bloquent COM7 actuellement."""
    blockers = []
    if not PSUTIL:
        return blockers
    my_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            pid = proc.info['pid']
            if pid == my_pid:
                continue
            name = proc.info['name'] or 'Unknown'
            try:
                for item in proc.open_files():
                    if 'COM7' in item.path.upper():
                        blockers.append(f'{name}(PID{pid})')
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return blockers


def _map_value(data, *keys):
    """Retourne la premiere valeur non-None trouvee dans data pour les keys donnees.
       Si aucune cle trouvee, retourne 0.0 au lieu de None (resilience Arduino)."""
    for k in keys:
        if k in data and data[k] is not None:
            return float(data[k]) if data[k] != '' else None
    return 0.0  # fallback: capteur absent ou non connecte


def _ensure_single_instance():
    """Empeche le lancement de plusieurs instances du bridge simultanement."""
    my_pid = os.getpid()
    if os.path.exists(BRIDGE_PID_FILE):
        try:
            with open(BRIDGE_PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            if old_pid != my_pid:
                if PSUTIL and psutil.pid_exists(old_pid):
                    print(f'[BRIDGE] Instance deja en cours (PID {old_pid}). Arret.')
                    sys.exit(0)
                else:
                    print(f'[BRIDGE] PID {old_pid} mort — suppression fichier verrou.')
                    os.remove(BRIDGE_PID_FILE)
        except (ValueError, OSError):
            try:
                os.remove(BRIDGE_PID_FILE)
            except OSError:
                pass
    with open(BRIDGE_PID_FILE, 'w') as f:
        f.write(str(my_pid))
    print(f'[BRIDGE] PID file cree : {BRIDGE_PID_FILE} (PID {my_pid})')


def main():
    global line_buf, sent_ok, sent_err

    _ensure_single_instance()

    print('=' * 60)
    print("  L'FELLAH BRIDGE SERIAL v7")
    print(f'  Port    : {SERIAL_PORT} @ {BAUDRATE} baud')
    print(f'  API     : {API_URL}')
    print(f'  Token   : {DEVICE_TOKEN[:8]}...')
    print('=' * 60)
    print()

    MAX_TRIES = 3
    tries = 0

    while True:
        try:
            killed = _force_free_com7()
            if killed:
                print(f'[CLEANUP] Attente 2s liberation port COM7...')
                time.sleep(2)
            try:
                ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
            except serial.SerialException as e:
                print(f'[SERIE] ERREUR ouverture {SERIAL_PORT}: {e}')
                raise
            ser.reset_input_buffer()
            print(f'[SERIE] Connexion reussie sur {SERIAL_PORT}')
            tries = 0  # reset on success

            if line_buf:
                print(f'[SERIE] Reprise buffer precedent: "{line_buf[:50]}..."')
            else:
                print('[SERIE] En attente des donnees...\n')

            last_heartbeat = time.time()
            last_raw_line = ""
            stagnation_count = 0
            last_data_received = time.time()
            warned_no_data = False
            while True:
                try:
                    now = time.time()
                    if now - last_heartbeat >= 5:
                        mode = 'SQLite (buffer)' if mysql_was_down else 'MySQL'
                        print(f"Bridge: Envoi... (OK {sent_ok}, ERR {sent_err}) — Mode: {mode}")
                        last_heartbeat = now

                    # ── Check irrigation command file ──────────
                    cmd_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'irrigation_command.txt')
                    if os.path.exists(cmd_file):
                        try:
                            with open(cmd_file, 'r') as f:
                                cmd = f.read().strip()
                            if cmd and ser and ser.is_open:
                                ser.write((cmd + '\n').encode('utf-8'))
                                ser.flush()
                                print(f'[IRRIGATION] Commande envoyee a Arduino: {cmd}')
                            os.remove(cmd_file)
                        except Exception as e:
                            print(f'[IRRIGATION] Erreur: {e}')
                    # ────────────────────────────────────────────

                    if ser.in_waiting == 0:
                        if line_buf:
                            data, line_buf = parse_complete_json(line_buf)
                            if data:
                                print(f'[SERIE] JSON (reprise buffer): {json.dumps(data)}')
                                send(data)
                        # Avertissement si aucune donnee n'arrive depuis 10s
                        if not warned_no_data and (now - last_data_received) > 10:
                            print(f"[WARNING] Rien recu du port serie depuis {(now-last_data_received):.0f}s. Verifiez le branchement ou le code Arduino.")
                            warned_no_data = True
                        time.sleep(0.05)
                        continue

                    print(f'[DEBUG] En attente de donnees sur {SERIAL_PORT}...')
                    raw_line = ser.readline()
                    if not raw_line:
                        continue
                    last_data_received = time.time()
                    warned_no_data = False

                    try:
                        line = raw_line.decode('utf-8', errors='replace').strip()
                    except Exception as e:
                        logger.error(f"Serial decode error: {e}", exc_info=True)
                        continue

                    # --- Détection de stagnation (freeze / boucle de buffer) ---
                    if line == last_raw_line:
                        stagnation_count += 1
                        if stagnation_count >= 3:
                            print(f"[ALERTE STAGNATION] Valeur identique {stagnation_count}x: {line[:80]}... Forçage reset_input_buffer()")
                            ser.reset_input_buffer()
                            stagnation_count = 0
                    else:
                        if stagnation_count > 0:
                            print(f"[STAGNATION] Fin apres {stagnation_count} iterations identiques.")
                        stagnation_count = 0
                        last_raw_line = line

                    print(f'[RAW SERIE] {repr(line[:200])}')

                    line_buf += line

                    while True:
                        data, line_buf = parse_complete_json(line_buf)
                        if data is None:
                            break
                        print(f'[SERIE] JSON extrait: {json.dumps(data)}')
                        send(data)

                    if len(line_buf) > MAX_LINE_LEN:
                        print(f'[SERIE] Buffer depasse {MAX_LINE_LEN} chars, reset')
                        line_buf = ""

                except serial.SerialException:
                    print('[SERIE] Deconnexion serie')
                    break
                except KeyboardInterrupt:
                    raise

            ser.close()

        except serial.SerialException as e:
            tries += 1
            err_str = str(e)
            print(f'[SERIE] Port {SERIAL_PORT} inaccessible (tentative {tries}/{MAX_TRIES}): {e}')
            if 'Access is denied' in err_str or 'denied' in err_str.lower() or 'PermissionError' in err_str:
                if tries >= MAX_TRIES:
                    blockers = _find_com7_blockers()
                    blocker_names = ', '.join(blockers) if blockers else 'processus inconnu'
                    print(f"[CRITICAL] Port COM7 bloque par {blocker_names}. Fermez-le manuellement.")
                    print("[CRITICAL] Arret du bridge. Relancez apres avoir libere COM7.")
                    sys.exit(1)
                else:
                    print(f'[SERIE] >>> Le port est probablement verrouille par le Serial Monitor Arduino <<<')
                    print(f'[SERIE] >>> Fermez le Serial Monitor et relancez le bridge. <<<')
            print(f'[SERIE] Retry dans {RETRY_DELAY}s...')
            time.sleep(RETRY_DELAY)
        except KeyboardInterrupt:
            print()
            break

    if 'ser' in locals() and ser.is_open:
        ser.close()
    if os.path.exists(BRIDGE_PID_FILE):
        os.remove(BRIDGE_PID_FILE)
        print(f'[BRIDGE] PID file supprime : {BRIDGE_PID_FILE}')
    print(f'BILAN: {sent_ok} OK / {sent_err} ERR')
    print('Arret.')


if __name__ == '__main__':
    main()
