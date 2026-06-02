# L'Fellah — Architecture IoT Capteurs

## Flux de donnees

```
ARDUINO (CAPTEURS) ──Serie (COM7, 9600 baud)──> [apps/bridge/]
                                                     bridge_serial.py
                                                        │
                                                        │ JSON {temp, hum, tds, ph}
                                                        ▼
                                                   HTTP POST
                                                        │
                                                        ▼
                                              [apps/sensors/]
                                                 views.py
                                               sensor_ingest()
                                                   │
                                         ┌─────────┴─────────┐
                                         │                   │
                                   services.py          serializers.py
                                  map_sensor_payload   SensorDataIngest
                                         │                   │
                                         └─────────┬─────────┘
                                                   ▼
                                            [Database]
                                         SensorData (BDD)
                                                   │
                                                   ▼
                                         [apps/sensors/]
                                           sensor_latest()
                                           sensor_chart()
                                                   │
                                             HTTP GET
                                                   │
                                                   ▼
                                        [apps/dashboard/]
                                      sensor_dashboard.html
                                             (JS Chart.js)
```

## Structure du projet

```
lfellah_project/
│
├── apps/
│   ├── sensors/                      # ← BACKEND (ingestion IoT)
│   │   ├── models.py                 # Device, SensorData
│   │   ├── serializers.py            # SensorDataIngestSerializer
│   │   ├── views.py                  # sensor_ingest(), sensor_latest()
│   │   ├── services.py               # map_sensor_payload(), validate_payload()
│   │   ├── urls.py                   # /api/sensors/ingest/
│   │   └── admin.py                  # Django Admin
│   │
│   ├── dashboard/                    # ← FRONTEND (affichage)
│   │   ├── views.py                  # dashboard_page()
│   │   ├── urls.py                   # /dashboard-iot/
│   │   └── templates/dashboard/
│   │       └── sensor_dashboard.html # JS + Chart.js (Live)
│   │
│   └── bridge/                       # ← COMMUNICATION SERIE
│       ├── bridge_serial.py          # Python (pyserial + requests)
│       └── diagnostic.py             # Test de la chaine
│
├── backend/
│   ├── lfellah_server/
│   │   ├── settings/base.py          # apps.sensors + apps.dashboard
│   │   └── urls.py                   # include('apps.sensors.urls')
│   ├── core/                         # Auth, weather, utilities
│   ├── accounts/                     # User model
│   ├── marketplace/
│   └── subscriptions/
│
├── bridge_serial.py                  # ← COPIE RACINE (lance depuis la racine)
├── test_inject.py                    # Test d'injection manual
└── diagnostic_capteurs.py            # Diagnostic de la chaine
```

## Endpoints API

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| POST | `/api/sensors/ingest/` | Aucune | Reception donnees Arduino (bridge) |
| GET | `/api/sensors/latest/` | Auth |Dernier releve + alertes |
| GET | `/api/sensors/chart/` | Auth | Donnees formatees Chart.js |
| GET | `/api/sensors/list/` | Auth | Liste des releves |
| GET | `/dashboard-iot/` | Auth | Page dashboard HTML |

## Installation

### 1. Creer la migration

```powershell
cd backend
python manage.py makemigrations sensors
python manage.py migrate
```

### 2. Creer un device de test

```python
# Dans Django shell: python manage.py shell
from apps.sensors.models import Device
from accounts.models import User

user = User.objects.first()
Device.objects.create(
    owner=user,
    device_type='arduino_uno',
    name='Arduino Capteurs',
    device_token='abcd1234sensor01',
    is_active=True,
)
```

### 3. Lancer le bridge

```powershell
python bridge_serial.py
```

### 4. Lancer le serveur

```powershell
cd backend
python manage.py runserver
```

### 5. Ouvrir le dashboard

```
http://localhost:8000/dashboard-iot/
```

## Mapping des cles JSON

| Arduino (brut) | Bridge | API (sensors) | Modele (BDD) |
|---------------|--------|---------------|-------------|
| `temp`, `T` | → temperature | temperature | temperature |
| `hum`, `H` | → humidity | humidity | humidity |
| `tds`, `TDS` | → tds | tds | tds |
| `ph`, `pH` | → ph | ph | ph |

Le bridge (`apps/bridge/bridge_serial.py`) normalise toutes les conventions
de nommage Arduino avant l'envoi a l'API via `map_sensor_payload()`.

## Debug

### Verifier le flux complet

```powershell
python diagnostic_capteurs.py
```

### Injecter des donnees manuellement

```powershell
python test_inject.py
```

### Lire les logs serveur Django

```
[SENSORS] ========== NEW READING ==========
[SENSORS] RAW JSON: {'device_token': '...', 'temperature': 25.3, ...}
[SENSORS] KEYS: ['device_token', 'temperature', ...]
[SENSORS] SAVED id=42 T=25.3 H=68.0 TDS=450 pH=6.8
[SENSORS] ===================================
```

## Conventions de nommage

- `apps.sensors` : tout le code relatif a l'ingestion (models, serializers, views)
- `apps.dashboard` : tout le code relatif a l'affichage (templates, views)
- `apps.bridge` : scripts de communication (bridge_serial.py, diagnostic.py)
- Les settings, wsgi, asgi restent dans `backend/lfellah_server/`
- Les URLs sont organisees par app (`apps.sensors.urls`, `apps.dashboard.urls`)