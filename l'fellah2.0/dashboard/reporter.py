# =============================================================
#  dashboard/reporter.py — Rapport terminal & statistiques
#
#  Affiche un résumé propre des données stockées en base.
#  Utilise uniquement des requêtes SQL (pas de lib externe).
# =============================================================

from database.queries import (
    get_plant, get_reading_history, get_decision_history,
    get_low_trust_sensors, get_all_plants
)
from database.db_manager import get_connection


class Reporter:
    """Génère des rapports lisibles depuis la base SQLite."""

    def print_summary(self, plant_id: int):
        """Affiche un résumé compact de l'état actuel."""
        plant = get_plant(plant_id)
        if not plant:
            print(f"[RAPPORT] Plante ID {plant_id} introuvable.")
            return

        history   = get_reading_history(plant_id, limit=5)
        decisions = get_decision_history(plant_id, limit=3)

        print(f"\n  ┌─ Rapport {plant['name']} ({plant['species']}) ─┐")

        if history:
            last = history[0]
            print(f"  │  Dernière lecture  : "
                  f"T={last['temperature']}°C  "
                  f"H={last['humidity']}%  "
                  f"pH={last['ph']}  "
                  f"Lux={last['light_lux']}")
            print(f"  │  Nb lectures total : {len(history)} (affiché: 5 dernières)")

        if decisions:
            print(f"  │  Dernière décision : {decisions[0]['action_type']}")
            executed = sum(1 for d in decisions if d['executed'])
            print(f"  │  Décisions exécutées : {executed}/{len(decisions)}")

        alerts = get_low_trust_sensors(threshold=0.5)
        if alerts:
            print(f"  │  Alertes capteurs  : {len(alerts)} anomalie(s) détectée(s)")
        print(f"  └{'─'*45}┘")

    def full_report(self, plant_id: int):
        """Affiche le rapport complet avec tout l'historique."""
        plant = get_plant(plant_id)
        if not plant:
            return

        print(f"\n{'═'*55}")
        print(f"  RAPPORT COMPLET — {plant['name']}")
        print(f"  Espèce   : {plant['species']}")
        print(f"  Lieu     : {plant['location']}")
        print(f"  Cibles   : T={plant['target_temp']}°C  H={plant['target_humidity']}%")
        print(f"{'═'*55}")

        # Statistiques SQL directes
        conn = get_connection()

        stats = conn.execute("""
            SELECT
                COUNT(*)        AS total,
                ROUND(AVG(temperature), 1) AS avg_t,
                ROUND(MIN(temperature), 1) AS min_t,
                ROUND(MAX(temperature), 1) AS max_t,
                ROUND(AVG(humidity), 1)    AS avg_h,
                ROUND(AVG(ph), 2)          AS avg_ph,
                ROUND(AVG(light_lux), 0)   AS avg_lux
            FROM sensor_readings WHERE plant_id = ?
        """, (plant_id,)).fetchone()

        if stats and stats['total'] > 0:
            print(f"\n  Capteurs ({stats['total']} lectures)")
            print(f"  Température : moy={stats['avg_t']}°C  "
                  f"min={stats['min_t']}°C  max={stats['max_t']}°C")
            print(f"  Humidité    : moy={stats['avg_h']}%")
            print(f"  pH          : moy={stats['avg_ph']}")
            print(f"  Luminosité  : moy={stats['avg_lux']} lux")

        # Décisions par type
        action_stats = conn.execute("""
            SELECT action_type,
                   COUNT(*) AS nb,
                   SUM(executed) AS exec
            FROM decisions WHERE plant_id = ?
            GROUP BY action_type
            ORDER BY nb DESC
        """, (plant_id,)).fetchall()

        if action_stats:
            print(f"\n  Décisions prises")
            for row in action_stats:
                print(f"  {row['action_type']:25s} "
                      f"× {row['nb']}  "
                      f"(exécutées: {row['exec']})")

        # Maladies détectées
        disease_stats = conn.execute("""
            SELECT stress_label, COUNT(*) AS nb,
                   ROUND(AVG(confidence)*100, 1) AS avg_conf
            FROM plant_images WHERE plant_id = ?
            GROUP BY stress_label
            ORDER BY nb DESC
            LIMIT 5
        """, (plant_id,)).fetchall()

        if disease_stats:
            print(f"\n  Vision IA — détections")
            for row in disease_stats:
                print(f"  {row['stress_label']:45s} "
                      f"× {row['nb']}  "
                      f"confiance moy: {row['avg_conf']}%")

        conn.close()

    def global_stats(self):
        """Statistiques globales de toutes les plantes."""
        plants = get_all_plants()
        print(f"\n  Système L'Fellah 2.0 — {len(plants)} plante(s) enregistrée(s)")
        for p in plants:
            print(f"  [{p['id']}] {p['name']} — {p['location']}")
