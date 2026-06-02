"""
Client météo OpenWeatherMap pour L'Fellah 2.0
Récupère les conditions climatiques en temps réel selon les coordonnées GPS.
"""
import urllib.request
import json


def get_weather(lat, lon, api_key=None):
    """
    Retourne les données météo pour une position GPS.
    Si pas de clé API, retourne des données nulles sans planter.
    """
    if not api_key or not lat or not lon:
        return {
            'temperature_c': None,
            'humidity_pct': None,
            'weather_condition': None
        }

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=fr"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'LFellah/2.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                'temperature_c': round(data['main']['temp'], 1),
                'humidity_pct': data['main']['humidity'],
                'weather_condition': data['weather'][0]['description'].capitalize()
            }
    except Exception as e:
        print(f"[WEATHER] Échec récupération météo: {e}")
        return {
            'temperature_c': None,
            'humidity_pct': None,
            'weather_condition': None
        }


def assess_disease_risk(temperature_c, humidity_pct, severity):
    """
    Évalue le risque de propagation basé sur les conditions météo.
    Retourne 'high', 'moderate', ou 'low'.
    """
    if severity == 'critical':
        if humidity_pct and humidity_pct > 75:
            return 'high'
        return 'moderate'
    if severity == 'warning':
        if humidity_pct and humidity_pct > 80 and temperature_c and 15 < temperature_c < 30:
            return 'moderate'
        return 'low'
    return 'low'
