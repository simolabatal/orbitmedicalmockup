# =============================================================
#  sensors/trust_score.py — Moteur de confiance des capteurs
#  Chaque capteur reçoit un score 0.0→1.0.
#  Score < 0.5 = anomalie → Safe Mode activé.
# =============================================================

from database.queries import insert_trust_score


# Plages physiquement réalistes pour chaque capteur
VALID_RANGES = {
    'temperature': (-10.0, 60.0),
    'humidity':    (0.0,   100.0),
    'ph':          (3.0,   10.0),
    'light_lux':   (0.0,   120_000.0),
}

# Plages normales d'une serre/jardin intérieur
NORMAL_RANGES = {
    'temperature': (10.0, 40.0),
    'humidity':    (20.0, 90.0),
    'ph':          (4.5,  8.5),
    'light_lux':   (0.0,  50_000.0),
}


class TrustScoreEngine:
    """
    Calcule un score de confiance pour chaque capteur selon 3 règles :
      1. Hors plage physique → score 0.0 (impossible réel)
      2. Hors plage normale  → score 0.3 (suspect)
      3. Dans la norme       → score 1.0
    """

    def _score_sensor(self, name: str, value: float) -> tuple[float, str | None]:
        low_valid, high_valid = VALID_RANGES[name]
        low_norm,  high_norm  = NORMAL_RANGES[name]

        if value < low_valid or value > high_valid:
            return 0.0, f"Valeur {value} hors plage physique [{low_valid}, {high_valid}]"

        if value < low_norm or value > high_norm:
            return 0.3, f"Valeur {value} suspecte (hors norme [{low_norm}, {high_norm}])"

        return 1.0, None

    def evaluate(self, reading: dict) -> dict:
        """
        Retourne un dict avec le score et la raison pour chaque capteur.
        Ex: {'temperature': {'score': 1.0, 'reason': None}, ...}
        """
        sensors = {
            'temperature': reading['temperature'],
            'humidity':    reading['humidity'],
            'ph':          reading['ph'],
            'light_lux':   reading['light_lux'],
        }
        results = {}
        for name, value in sensors.items():
            score, reason = self._score_sensor(name, value)
            results[name] = {'score': score, 'reason': reason}
        return results

    def save(self, reading_id: int, scores: dict):
        """Persiste tous les scores en base de données."""
        for sensor_type, info in scores.items():
            insert_trust_score(
                reading_id=reading_id,
                sensor_type=sensor_type,
                score=info['score'],
                anomaly_reason=info['reason']
            )

    def global_trust(self, scores: dict) -> float:
        """Score moyen global (0.0 → 1.0)."""
        return sum(v['score'] for v in scores.values()) / len(scores)

    def is_safe_mode(self, scores: dict, threshold: float = 0.5) -> bool:
        """True si au moins un capteur est sous le seuil de confiance."""
        return any(v['score'] < threshold for v in scores.values())
