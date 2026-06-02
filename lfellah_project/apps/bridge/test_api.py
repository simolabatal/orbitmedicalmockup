#!/usr/bin/env python
"""Quick test of sensor API endpoints."""
import sys, os, json, urllib.request, urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lfellah_server.settings')
import django
django.setup()

from django.urls import reverse, resolve
from iot.models import Device, SensorData

BASE = 'http://127.0.0.1:8000'

print('=== AUDIT URLS ===')

urls_to_test = [
    '/api/sensors/ingest/',
    '/api/sensors/latest/',
    '/api/sensors/chart/',
    '/dashboard-iot/',
]

for url in urls_to_test:
    try:
        req = urllib.request.Request(BASE + url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f'  {url} -> HTTP {resp.status}')
    except urllib.error.HTTPError as e:
        print(f'  {url} -> HTTP {e.code}')
    except Exception as e:
        print(f'  {url} -> {type(e).__name__}: {str(e)[:60]}')

print()
print('=== TEST POST ===')

payload = {
    'device_token': 'abcd1234sensor01',
    'temperature': 33.1,
    'humidity': 42.0,
    'tds': 450,
    'ph': 6.5,
}
body = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(
    BASE + '/api/sensors/ingest/',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print(f'  POST -> HTTP {resp.status}: {result}')
except urllib.error.HTTPError as e:
    print(f'  POST -> HTTP {e.code}: {e.read().decode()[:200]}')
except Exception as e:
    print(f'  POST -> {type(e).__name__}: {str(e)[:60]}')

print()
print('=== DB CHECK ===')
count = SensorData.objects.count()
print(f'  SensorData count: {count}')
if count > 0:
    latest = SensorData.objects.order_by('-recorded_at').first()
    print(f'  Latest: T={latest.temperature} H={latest.humidity} TDS={latest.tds} pH={latest.ph}')