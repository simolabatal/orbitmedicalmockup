import json


def parse_json_buffer(raw_text):
    """
    Parse le buffer texte et retourne la liste des JSON valides extraits.
    Gere les cas ou { et } sont sur des lignes separees.
    """
    raw_text = raw_text.strip()
    if not raw_text:
        return []

    results = []
    start = raw_text.find('{')

    while start != -1:
        json_candidate = raw_text[start:]

        if '}' not in json_candidate:
            break

        end = json_candidate.find('}')
        if end == -1:
            break

        json_str = json_candidate[:end + 1]
        try:
            data = json.loads(json_str)
            results.append(data)
            raw_text = json_candidate[end + 1:]
        except json.JSONDecodeError:
            raw_text = json_candidate[end + 1:]

        start = raw_text.find('{')

    return results


def map_sensor_payload(data):
    """
    Mappe les champs JSON recus par le bridge vers les champs du modele SensorData.
    Gere les conventions de nommage Arduino (temp, hum, T, H) et standard (temperature, humidity).
    """
    if not data:
        return None

    mapped = {}

    temp_keys = ['temperature', 'temp', 'Temperature', 'T', 'air_temp']
    hum_keys  = ['humidity', 'hum', 'Humidity', 'H', 'air_humidity']
    tds_keys  = ['tds', 'TDS', 'Tds']
    ph_keys   = ['ph', 'pH', 'PH', 'Ph']

    def _extract(keys):
        for k in keys:
            if k in data and data[k] not in (None, '', 'null'):
                try:
                    val = float(data[k])
                    return val
                except (ValueError, TypeError):
                    continue
        return None

    mapped['temperature'] = _extract(temp_keys)
    mapped['humidity']    = _extract(hum_keys)
    mapped['tds']         = _extract(tds_keys)
    mapped['ph']          = _extract(ph_keys)
    mapped['device_token'] = data.get('device_token', '')

    return mapped if mapped.get('device_token') else None


def validate_payload(payload):
    """
    Valide qu'un payload mappe contient les champs minimaux requis.
    Retourne (bool, list_of_missing_fields).
    """
    if not payload:
        return False, ['payload is None or empty']

    required = ['device_token']
    optional = ['temperature', 'humidity', 'tds', 'ph']
    all_fields = required + optional

    missing = []
    for field in required:
        val = payload.get(field)
        if not val or val == '':
            missing.append(field)

    has_sensor_data = any(
        payload.get(f) is not None
        for f in optional
    )
    if not has_sensor_data:
        missing.append('at least one sensor value (temperature/humidity/tds/ph)')

    return len(missing) == 0, missing


def sanitize_float(value, default=None):
    """Convertit en float de maniere sure, retourne default si echec."""
    try:
        if value is None or value == '' or value == 'null':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default
