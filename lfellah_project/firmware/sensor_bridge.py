#!/usr/bin/env python
"""
L'Fellah Sensor Bridge — Lit les donnees serie depuis l'Arduino
et les envoie a l'API Django via HTTP POST.

Usage :
    python sensor_bridge.py COM3

Configuration :
    Modifier DEVICE_TOKEN et API_URL ci-dessous.
"""

import json
import sys
import time
import urllib.request
import urllib.error

# ─── CONFIGURATION ──────────────────────────────────────────────
SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
BAUDRATE = 9600
DEVICE_TOKEN = 'CHANGEZ_MOI_AVEC_LE_TOKEN_DE_VOTRE_DEVICE'
API_URL = 'http://localhost:8000/api/iot/sensor-data/v2/'
RETRY_DELAY = 3  # secondes entre les retries
# ─────────────────────────────────────────────────────────────────


def send_to_api(data):
    """Envoie les donnees capteurs a l'API Django."""
    payload = {
        'device_token': DEVICE_TOKEN,
        **data
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(f'[API] OK — id={result.get("id")} device={result.get("device")}')
            return True
    except urllib.error.HTTPError as e:
        print(f'[API] HTTP {e.code}: {e.read().decode()[:100]}')
    except urllib.error.URLError as e:
        print(f'[API] Erreur reseau: {e.reason}')
    except Exception as e:
        print(f'[API] Erreur: {e}')
    return False


def main():
    try:
        import serial
    except ImportError:
        print("Erreur : pyserial n'est pas installe.")
        print("Installez-le avec : pip install pyserial")
        sys.exit(1)

    print(f"L'Fellah Sensor Bridge — demarrage...")
    print(f"Port: {SERIAL_PORT} | Baud: {BAUDRATE}")
    print(f"API: {API_URL}")
    print(f"Device: {DEVICE_TOKEN[:8]}...")
    print()

    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=5)
            print(f"[SERIE] Connecte a {SERIAL_PORT}")

            while True:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue

                    print(f'[SERIE] Recu: {line[:120]}')

                    # Parser le JSON (peut contenir des caracteres parasites,
                    # on extrait le premier objet JSON valide)
                    start = line.find('{')
                    end = line.rfind('}')
                    if start == -1 or end == -1:
                        print('[SERIE] JSON invalide, ignore')
                        continue

                    json_str = line[start:end + 1]
                    data = json.loads(json_str)

                    # Envoyer a l'API
                    send_to_api(data)

                except json.JSONDecodeError:
                    print('[SERIE] Erreur parsing JSON')
                except serial.SerialException:
                    print('[SERIE] Deconnecte, tentative de reconnexion...')
                    break
                except KeyboardInterrupt:
                    raise

            ser.close()

        except serial.SerialException as e:
            print(f'[SERIE] Impossible d\'ouvrir {SERIAL_PORT}: {e}')
            print(f'[SERIE] Nouvelle tentative dans {RETRY_DELAY}s...')
            time.sleep(RETRY_DELAY)
        except KeyboardInterrupt:
            print('\nArret demande.')
            break

    if 'ser' in locals() and ser.is_open:
        ser.close()
    print('Bridge arrete.')


if __name__ == '__main__':
    main()
