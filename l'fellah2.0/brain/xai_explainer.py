# =============================================================
#  brain/xai_explainer.py — IA Explicable (XAI)
#
#  Génère une explication lisible par un humain pour chaque
#  décision prise, en listant les facteurs déclencheurs.
#  Sauvegarde aussi le log XAI en base de données.
# =============================================================

import json
from database.queries import insert_xai_log


class XAIExplainer:
    """
    Produit des explications naturelles des décisions IA.

    Exemple de sortie :
    "Irrigation déclenchée car : humidité sol = 22% (seuil : 30%),
     température = 36°C (élevée), plante montre une maladie fongique
     (Tomato Early blight, confiance 78%)."
    """

    def _build_factors(self, reading: dict, vision: dict,
                       trust_scores: dict) -> list[str]:
        """Construit la liste des facteurs observés."""
        factors = []

        # Capteurs
        t = reading.get('temperature', 0)
        h = reading.get('humidity', 0)
        ph = reading.get('ph', 0)
        lux = reading.get('light_lux', 0)

        if t > 35:
            factors.append(f"température élevée ({t}°C)")
        elif t < 8:
            factors.append(f"température trop basse ({t}°C)")
        else:
            factors.append(f"température normale ({t}°C)")

        if h < 30:
            factors.append(f"humidité sol très faible ({h}%)")
        elif h < 50:
            factors.append(f"humidité sol basse ({h}%)")
        elif h > 85:
            factors.append(f"humidité sol trop élevée ({h}%)")
        else:
            factors.append(f"humidité sol normale ({h}%)")

        if ph < 5.5:
            factors.append(f"pH acide ({ph})")
        elif ph > 7.5:
            factors.append(f"pH basique ({ph})")
        else:
            factors.append(f"pH normal ({ph})")

        if lux < 500:
            factors.append(f"luminosité insuffisante ({lux:.0f} lux)")

        # Vision IA
        if not vision.get('is_healthy', True):
            factors.append(
                f"maladie détectée : {vision['label']} "
                f"(confiance {vision['confidence']*100:.0f}%)"
            )
        else:
            factors.append(f"plante visuellement saine ({vision['label']})")

        # Trust Score
        anomalies = [
            k for k, v in trust_scores.items()
            if v['score'] < 0.5
        ]
        if anomalies:
            factors.append(f"capteurs non fiables : {', '.join(anomalies)}")

        return factors

    def _action_to_french(self, action: str) -> str:
        translations = {
            "irrigation"        : "Irrigation déclenchée",
            "ventilation"       : "Ventilation activée",
            "heating"           : "Chauffage activé",
            "lighting"          : "Éclairage artificiel activé",
            "reduce_watering"   : "Arrosage réduit",
            "ph_correction_up"  : "Correction pH (augmentation)",
            "ph_correction_down": "Correction pH (diminution)",
            "safe_mode"         : "Safe Mode activé (capteurs non fiables)",
            "monitor"           : "Surveillance continue",
            "disease_alert"     : "Alerte maladie envoyée",
        }
        return translations.get(action, action)

    def explain(self, reading: dict, vision: dict,
                decision: dict, trust_scores: dict) -> str:
        """
        Génère l'explication complète en français.
        Sauvegarde en base et retourne la chaîne.
        """
        action_fr = self._action_to_french(decision['action_type'])
        factors   = self._build_factors(reading, vision, trust_scores)

        # Construire la phrase
        explanation = (
            f"{action_fr} — Facteurs : "
            + " | ".join(factors)
            + "."
        )

        # Sauvegarde SQL
        insert_xai_log(
            decision_id=decision['decision_id'],
            explanation=explanation,
            factors=json.dumps(factors, ensure_ascii=False)
        )

        return explanation
