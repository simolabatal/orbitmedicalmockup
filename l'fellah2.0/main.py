# =============================================================
#  L'Fellah 2.0 — Point d'entrée principal
# =============================================================

from database.db_manager import init_db
from database.queries import add_plant, get_all_plants
from sensors.sensor_simulator import SensorSimulator
from sensors.trust_score import TrustScoreEngine
from vision.plant_classifier import PlantClassifier
from brain.decision_engine import DecisionEngine
from brain.digital_twin import DigitalTwin
from brain.xai_explainer import XAIExplainer
from dashboard.reporter import Reporter

import time

def run_cycle(plant_id: int, sensor_sim: SensorSimulator,
              trust_engine: TrustScoreEngine, classifier: PlantClassifier,
              decision_engine: DecisionEngine, twin: DigitalTwin,
              explainer: XAIExplainer, reporter: Reporter):
    """Un cycle complet de surveillance pour une plante."""

    print(f"\n{'='*55}")
    print(f"  Cycle L'Fellah 2.0 — Plante ID {plant_id}")
    print(f"{'='*55}")

    # 1. Lecture capteurs
    reading = sensor_sim.read(plant_id)
    print(f"\n[CAPTEURS] T={reading['temperature']}°C  "
          f"H={reading['humidity']}%  "
          f"pH={reading['ph']}  "
          f"Lux={reading['light_lux']}")

    # 2. Trust Score
    scores = trust_engine.evaluate(reading)
    trust_engine.save(reading['reading_id'], scores)
    alerts = [k for k, v in scores.items() if v['score'] < 0.5]
    if alerts:
        print(f"[TRUST]   Anomalie détectée sur : {alerts}")
    else:
        print(f"[TRUST]   Tous les capteurs fiables")

    # 3. Vision IA (classification plante)
    vision_result = classifier.classify(plant_id)
    print(f"[VISION]  {vision_result['label']} "
          f"(confiance: {vision_result['confidence']*100:.1f}%)")

    # 4. Décision IA
    decision = decision_engine.decide(plant_id, reading, vision_result, scores)
    print(f"[DÉCISION] Action → {decision['action_type']}")

    # 5. Digital Twin — simulation avant exécution
    sim = twin.simulate(decision['decision_id'], reading, decision)
    if sim['is_safe']:
        print(f"[TWIN]    Simulation OK (risque={sim['risk_score']:.2f}) → EXÉCUTION")
        decision_engine.execute(decision['decision_id'])
    else:
        print(f"[TWIN]    Simulation RISQUÉE (risque={sim['risk_score']:.2f}) → ANNULÉ")

    # 6. Explication XAI
    explanation = explainer.explain(reading, vision_result, decision, scores)
    print(f"[XAI]     {explanation}")

    # 7. Rapport
    reporter.print_summary(plant_id)


def main():
    print("\n  L'Fellah 2.0 — Système IA Agriculture Intelligente")
    print("  " + "─" * 50)

    # Initialisation base de données
    init_db()

    # Création d'une plante de test si aucune n'existe
    plants = get_all_plants()
    if not plants:
        pid = add_plant(
            name="Tomate 01",
            species="Solanum lycopersicum",
            location="Serre A",
            target_humidity=65.0,
            target_temp=22.0
        )
        print(f"  Plante créée (ID={pid})")
        plant_id = pid
    else:
        plant_id = plants[0]['id']
        print(f"  Plante chargée : {plants[0]['name']} (ID={plant_id})")

    # Initialisation des modules
    sensor_sim     = SensorSimulator()
    trust_engine   = TrustScoreEngine()
    classifier     = PlantClassifier()
    decision_engine = DecisionEngine()
    twin           = DigitalTwin()
    explainer      = XAIExplainer()
    reporter       = Reporter()

    # Boucle principale — 3 cycles de démonstration
    for cycle in range(1, 4):
        print(f"\n>>> Cycle {cycle}/3")
        run_cycle(plant_id, sensor_sim, trust_engine, classifier,
                  decision_engine, twin, explainer, reporter)
        if cycle < 3:
            time.sleep(1)

    print("\n  Fin de la démonstration L'Fellah 2.0")
    print("  Consulte fellah.db avec DB Browser for SQLite")
    print("  pour visualiser toutes les données enregistrées.\n")


if __name__ == "__main__":
    main()
