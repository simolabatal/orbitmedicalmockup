#!/usr/bin/env python
"""
L'Fellah — Diagnostic de la chaine capteurs
Teste: Modele → API ingest → API lecture → Bridge Serial → Dashboard

Usage : python apps/bridge/diagnostic.py
"""

import os, sys, json, time, urllib.request, urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lfellah_server.settings')
import django
django.setup()

from iot.models import Device, SensorData

DEVICE_TOKEN = 'abcd1234sensor01'
API_BASE = 'http://127.0.0.1:8000'
PASSED, FAILED = 0, 0

def check(name, condition, detail=''):
    global PASSED, FAILED
    if condition:
        print(f'  [OK] {name} {detail}')
        PASSED += 1
    else:
        print(f'  [FAIL] {name} {detail}')
        FAILED += 1

print('=' * 55)
print('  DIAGNOSTIC CHAINE CAPTEURS L\'FELLAH')
print('=' * 55)

print('\n>>> 1. MODELE SensorData')
device = Device.objects.filter(device_token=DEVICE_TOKEN, is_active=True).first()
check('Device existe', device is not None, DEVICE_TOKEN if device else 'AUCUN device')
if device:
    check('Device actif', device.is_active)
    latest = SensorData.objects.filter(device=device).order_by('-recorded_at').first()
    if latest:
        check('Temperature', latest.temperature is not None, f'{latest.temperature}C')
        check('Humidity', latest.humidity is not None, f'{latest.humidity}%')
        check('TDS', latest.tds is not None, f'{latest.tds} ppm')
        check('pH', latest.ph is not None, f'{latest.ph}')

print('\n>>> 2. API INGEST (/api/sensors/ingest/)')
if device:
    test_data = {
        'device_token': DEVICE_TOKEN,
        'temperature': round(22.0 + (time.time() % 10), 1),
        'humidity': round(60.0 + (time.time() % 20), 1),
        'tds': 420 + int(time.time() % 100),
        'ph': round(6.5 + (time.time() % 10) / 10, 1),
    }
    try:
        body = json.dumps(test_data).encode('utf-8')
        req = urllib.request.Request(
            f'{API_BASE}/api/sensors/ingest/',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            check('POST 201', resp.status == 201, f'status={resp.status}')
            check('Response status=ok', result.get('status') == 'ok', f'id={result.get("id")}')
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()[:100]
        check('POST reussi', False, f'HTTP {e.code}: {body_err}')
    except Exception as e:
        check('POST reussi', False, str(e))

print('\n>>> 3. API LECTURE (/api/sensors/latest/)')
if device:
    try:
        req = urllib.request.Request(
            f'{API_BASE}/api/sensors/latest/',
            headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            check('has_data', data.get('has_data') == True)
            if data.get('has_data'):
                check('temperature', data.get('temperature') is not None, str(data.get('temperature')))
                check('alerts', 'alerts' in data)
    except urllib.error.HTTPError as e:
        check('GET reussi', False, f'HTTP {e.code}')
    except Exception as e:
        check('GET reussi', False, str(e))

print('\n>>> 4. DEVICE TOKEN')
check('Token longueur', len(DEVICE_TOKEN) >= 8, f'{len(DEVICE_TOKEN)} chars')
check('Token en BDD', Device.objects.filter(device_token=DEVICE_TOKEN).exists(), 'trouve' if Device.objects.filter(device_token=DEVICE_TOKEN).exists() else 'INTROUVABLE')

print('\n>>> 5. DASHBOARD')
frontend_ok = os.path.exists(os.path.join(os.path.dirname(__file__), 'dashboard', 'templates', 'dashboard', 'sensor_dashboard.html'))
check('Template dashboard', frontend_ok)

with open(os.path.join(os.path.dirname(__file__), 'bridge_serial.py')) as f:
    bridge_code = f.read()
check('Bridge pointe /api/sensors/ingest', '/api/sensors/ingest' in bridge_code)
check('Bridge token', DEVICE_TOKEN[:8] in bridge_code)

print('\n' + '=' * 55)
print(f'  RESULTAT : {PASSED} OK / {FAILED} ECHECS')
print('=' * 55)
if FAILED == 0:
    print('\nChaine complete OK!')
else:
    print('\nCorriger les echecs ci-dessus.')