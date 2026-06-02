# =============================================================
#  sensors/sensor_simulator.py — Simulation des capteurs
#  Simule température, humidité, pH, luminosité avec bruit
#  réaliste. Prêt à être remplacé par de vrais capteurs GPIO.
# =============================================================

import random
import math
from datetime import datetime
from database.queries import insert_reading, get_plant


class SensorSimulator:
    """
    Simule les 4 capteurs avec :
    - Valeurs de base proches des cibles de la plante
    - Bruit gaussien réaliste
    - Pannes aléatoires occasionnelles (pour tester Trust Score)
    - Variation selon l'heure du jour (lumière naturelle)
    """

    def __init__(self, anomaly_rate: float = 0.10):
        """
        anomaly_rate : probabilité d'une lecture anormale (0.10 = 10%)
        """
        self.anomaly_rate = anomaly_rate

    # ── Helpers ───────────────────────────────────────────────

    def _hour_factor(self) -> float:
        """Facteur lumineux selon l'heure (0.0 la nuit, 1.0 à midi)."""
        h = datetime.now().hour
        return max(0.0, math.sin((h - 6) * math.pi / 12))

    def _maybe_anomaly(self, value: float, sensor: str) -> float:
        """Introduit une anomalie aléatoire selon anomaly_rate."""
        if random.random() < self.anomaly_rate:
            # Anomalie : valeur hors plage réaliste
            spike = random.choice([-1, 1]) * random.uniform(15, 30)
            return round(value + spike, 2)
        return value

    # ── Lectures individuelles ────────────────────────────────

    def read_temperature(self, target: float = 22.0) -> float:
        base = target + random.gauss(0, 2.5)
        return round(self._maybe_anomaly(base, "temperature"), 2)

    def read_humidity(self, target: float = 60.0) -> float:
        base = target + random.gauss(0, 5.0)
        base = max(5.0, min(100.0, base))
        return round(self._maybe_anomaly(base, "humidity"), 2)

    def read_ph(self) -> float:
        base = random.gauss(6.5, 0.3)
        base = max(4.0, min(9.0, base))
        return round(self._maybe_anomaly(base, "ph"), 2)

    def read_light(self) -> float:
        factor = self._hour_factor()
        base = factor * random.gauss(5000, 800) + random.gauss(50, 20)
        base = max(0.0, base)
        return round(self._maybe_anomaly(base, "light_lux"), 1)

    # ── Lecture complète ──────────────────────────────────────

    def read(self, plant_id: int) -> dict:
        """
        Lit tous les capteurs, sauvegarde en base et retourne un dict.
        Si la plante a des cibles définies, elles sont utilisées.
        """
        plant = get_plant(plant_id)
        target_temp = plant['target_temp'] if plant else 22.0
        target_hum  = plant['target_humidity'] if plant else 60.0

        temperature = self.read_temperature(target_temp)
        humidity    = self.read_humidity(target_hum)
        ph          = self.read_ph()
        light_lux   = self.read_light()

        # Sauvegarde SQL
        reading_id = insert_reading(
            plant_id=plant_id,
            temperature=temperature,
            humidity=humidity,
            ph=ph,
            light_lux=light_lux
        )

        return {
            'reading_id' : reading_id,
            'plant_id'   : plant_id,
            'temperature': temperature,
            'humidity'   : humidity,
            'ph'         : ph,
            'light_lux'  : light_lux,
            'target_temp': target_temp,
            'target_hum' : target_hum,
        }
