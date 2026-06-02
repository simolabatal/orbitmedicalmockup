# =============================================================
#  brain/decision_engine.py — Moteur de décision IA central
#
#  Fusionne données capteurs + vision + trust scores
#  pour décider quelle action prendre.
#  Respecte la philosophie : moins d'eau, moins d'énergie,
#  moins d'intervention = meilleure santé plante.
# =============================================================

from database.queries import (
    insert_decision, mark_decision_executed, get_plant
)


# ─────────────────────────────────────────────────────────────
#  Règles de décision (système expert)
#  Chaque règle retourne (action, priorité, raison)
# ─────────────────────────────────────────────────────────────

class DecisionEngine:
    """
    Moteur de décision par règles explicables.
    Chaque règle est une condition claire → action précise.
    Priorité : plus le chiffre est élevé, plus c'est urgent.
    """

    # Seuils configurables
    TEMP_HIGH      = 35.0    # °C — trop chaud
    TEMP_LOW       = 8.0     # °C — trop froid
    HUMIDITY_LOW   = 30.0    # %  — trop sec → irrigation
    HUMIDITY_HIGH  = 85.0    # %  — trop humide → risque moisissure
    PH_LOW         = 5.5     # pH acide
    PH_HIGH        = 7.5     # pH basique
    LIGHT_LOW      = 500.0   # lux — trop sombre
    TRUST_ALERT    = 0.5     # seuil anomalie capteur

    def _evaluate_rules(self, reading: dict, vision: dict,
                        trust_scores: dict, plant: dict) -> list:
        """
        Évalue toutes les règles et retourne une liste de
        (priorité, action, raison) triée par priorité décroissante.
        """
        rules = []

        # ── Sécurité capteur (Trust Score) ────────────────────
        bad_sensors = [k for k, v in trust_scores.items()
                       if v['score'] < self.TRUST_ALERT]
        if bad_sensors:
            rules.append((90, "safe_mode",
                f"Capteur(s) non fiable(s) : {bad_sensors}. "
                "Passage en Safe Mode — aucune action automatique."))

        # ── Température critique ───────────────────────────────
        if reading['temperature'] > self.TEMP_HIGH:
            rules.append((80, "ventilation",
                f"Température {reading['temperature']}°C > {self.TEMP_HIGH}°C. "
                "Activer ventilation et ombrage."))

        if reading['temperature'] < self.TEMP_LOW:
            rules.append((80, "heating",
                f"Température {reading['temperature']}°C < {self.TEMP_LOW}°C. "
                "Activer chauffage."))

        # ── Humidité / irrigation ──────────────────────────────
        if reading['humidity'] < self.HUMIDITY_LOW:
            urgency = 70
            # Si la plante est aussi stressée → plus urgent
            if not vision['is_healthy']:
                urgency = 85
            rules.append((urgency, "irrigation",
                f"Humidité {reading['humidity']}% < {self.HUMIDITY_LOW}%. "
                f"Plante : {vision['label']} (confiance {vision['confidence']*100:.0f}%). "
                "Irrigation nécessaire."))

        if reading['humidity'] > self.HUMIDITY_HIGH:
            rules.append((60, "reduce_watering",
                f"Humidité {reading['humidity']}% > {self.HUMIDITY_HIGH}%. "
                "Risque de moisissure. Réduire arrosage, améliorer aération."))

        # ── pH ─────────────────────────────────────────────────
        if reading['ph'] < self.PH_LOW:
            rules.append((50, "ph_correction_up",
                f"pH {reading['ph']} trop acide (< {self.PH_LOW}). "
                "Ajouter chaux ou bicarbonate."))

        if reading['ph'] > self.PH_HIGH:
            rules.append((50, "ph_correction_down",
                f"pH {reading['ph']} trop basique (> {self.PH_HIGH}). "
                "Ajouter soufre ou engrais acide."))

        # ── Luminosité ─────────────────────────────────────────
        if reading['light_lux'] < self.LIGHT_LOW:
            rules.append((40, "lighting",
                f"Luminosité {reading['light_lux']} lux < {self.LIGHT_LOW} lux. "
                "Activer éclairage artificiel."))

        # ── Maladie détectée ───────────────────────────────────
        if not vision['is_healthy'] and vision['confidence'] >= 0.65:
            rules.append((75, "disease_alert",
                f"Maladie détectée : {vision['label']} "
                f"(confiance {vision['confidence']*100:.0f}%). "
                "Inspection manuelle recommandée."))

        # ── Tout va bien ───────────────────────────────────────
        if not rules:
            rules.append((10, "monitor",
                "Tous les paramètres dans les normes. Surveillance continue."))

        # Trier par priorité décroissante
        rules.sort(key=lambda x: x[0], reverse=True)
        return rules

    def decide(self, plant_id: int, reading: dict,
               vision: dict, trust_scores: dict) -> dict:
        """
        Prend la décision de plus haute priorité,
        la sauvegarde en base et la retourne.
        """
        plant = get_plant(plant_id)
        rules = self._evaluate_rules(reading, vision, trust_scores, plant)

        # Décision principale = règle de plus haute priorité
        priority, action, explanation = rules[0]

        decision_id = insert_decision(
            plant_id=plant_id,
            action_type=action,
            explanation=explanation
        )

        return {
            'decision_id': decision_id,
            'plant_id'   : plant_id,
            'action_type': action,
            'explanation': explanation,
            'priority'   : priority,
            'all_rules'  : rules,
        }

    def execute(self, decision_id: int):
        """Marque la décision comme exécutée en base."""
        mark_decision_executed(decision_id)
