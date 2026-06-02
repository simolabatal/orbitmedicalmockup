# =============================================================
#  brain/digital_twin.py — Jumeau numérique (Digital Twin)
#
#  Avant toute action, simule son impact sur des valeurs
#  virtuelles identiques aux conditions réelles.
#  Si le résultat simulé est dangereux → décision annulée.
# =============================================================

from database.queries import insert_simulation, get_avg_readings


class DigitalTwin:
    """
    Simule l'effet d'une action sur l'état de la plante
    avant de l'exécuter réellement.

    Chaque action a un effet modélisé :
    - irrigation       : +15% humidité
    - ventilation      : -3°C température
    - heating          : +5°C température
    - lighting         : +2000 lux
    - reduce_watering  : -10% humidité
    - etc.
    """

    # Effets simulés par action (delta sur les capteurs)
    ACTION_EFFECTS = {
        "irrigation": {
            "humidity": +15.0, "temperature": -1.0
        },
        "ventilation": {
            "temperature": -3.0, "humidity": -5.0
        },
        "heating": {
            "temperature": +5.0
        },
        "lighting": {
            "light_lux": +2000.0
        },
        "reduce_watering": {
            "humidity": -10.0
        },
        "ph_correction_up": {
            "ph": +0.5
        },
        "ph_correction_down": {
            "ph": -0.5
        },
        "safe_mode": {},      # aucun effet physique
        "monitor":   {},
        "disease_alert": {},
    }

    # Plages sûres après action
    SAFE_BOUNDS = {
        "temperature": (5.0,  45.0),
        "humidity":    (10.0, 95.0),
        "ph":          (4.0,  9.0),
        "light_lux":   (0.0,  80_000.0),
    }

    def simulate(self, decision_id: int,
                 current_reading: dict, decision: dict) -> dict:
        """
        Simule l'action sur l'état courant.
        Retourne: {'is_safe': bool, 'risk_score': float,
                   'simulated_state': str, 'new_values': dict}
        """
        action = decision['action_type']
        effects = self.ACTION_EFFECTS.get(action, {})

        # Appliquer les effets aux valeurs actuelles
        new_values = {
            'temperature': current_reading.get('temperature', 22.0),
            'humidity'   : current_reading.get('humidity', 60.0),
            'ph'         : current_reading.get('ph', 6.5),
            'light_lux'  : current_reading.get('light_lux', 3000.0),
        }
        for sensor, delta in effects.items():
            if sensor in new_values:
                new_values[sensor] = round(new_values[sensor] + delta, 2)

        # Vérification des bornes de sécurité
        violations = []
        risk_score = 0.0

        for sensor, value in new_values.items():
            low, high = self.SAFE_BOUNDS[sensor]
            if value < low:
                violations.append(
                    f"{sensor}={value} sous le minimum ({low})"
                )
                risk_score += 0.25
            elif value > high:
                violations.append(
                    f"{sensor}={value} au-dessus du maximum ({high})"
                )
                risk_score += 0.25

        is_safe = len(violations) == 0
        risk_score = min(risk_score, 1.0)

        # Description de l'état simulé
        if is_safe:
            state_desc = (
                f"Après {action} : "
                f"T={new_values['temperature']}°C, "
                f"H={new_values['humidity']}%, "
                f"pH={new_values['ph']}, "
                f"Lux={new_values['light_lux']}"
            )
        else:
            state_desc = f"RISQUE détecté : {'; '.join(violations)}"

        # Sauvegarde en base
        insert_simulation(
            decision_id=decision_id,
            simulated_state=state_desc,
            is_safe=is_safe,
            risk_score=risk_score
        )

        return {
            'is_safe'        : is_safe,
            'risk_score'     : risk_score,
            'simulated_state': state_desc,
            'new_values'     : new_values,
            'violations'     : violations,
        }
