# =============================================================
#  database/db_manager.py — Connexion & initialisation SQLite
# =============================================================

import sqlite3
import os

# Le fichier .db est créé dans le dossier racine du projet
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fellah.db")


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion avec accès par nom de colonne."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crée toutes les tables si elles n'existent pas encore."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""

        -- Plantes enregistrées dans le système
        CREATE TABLE IF NOT EXISTS plants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            species         TEXT,
            location        TEXT,
            target_humidity REAL    DEFAULT 60.0,
            target_temp     REAL    DEFAULT 22.0,
            planted_at      DATE    DEFAULT (date('now'))
        );

        -- Lectures des capteurs physiques (ou simulés)
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id    INTEGER NOT NULL,
            temperature REAL,
            humidity    REAL,
            ph          REAL,
            light_lux   REAL,
            timestamp   DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        );

        -- Résultats de la vision IA (classification feuille)
        CREATE TABLE IF NOT EXISTS plant_images (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id     INTEGER NOT NULL,
            image_path   TEXT,
            stress_label TEXT,
            confidence   REAL,
            captured_at  DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        );

        -- Score de confiance par capteur
        CREATE TABLE IF NOT EXISTS trust_scores (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id     INTEGER NOT NULL,
            sensor_type    TEXT,
            score          REAL,
            anomaly_reason TEXT,
            evaluated_at   DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (reading_id) REFERENCES sensor_readings(id)
        );

        -- Décisions prises par le moteur IA
        CREATE TABLE IF NOT EXISTS decisions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id    INTEGER NOT NULL,
            action_type TEXT,
            explanation TEXT,
            executed    INTEGER DEFAULT 0,
            decided_at  DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        );

        -- Simulations du jumeau numérique avant exécution
        CREATE TABLE IF NOT EXISTS digital_twin_sims (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id     INTEGER NOT NULL,
            simulated_state TEXT,
            is_safe         INTEGER DEFAULT 1,
            risk_score      REAL    DEFAULT 0.0,
            simulated_at    DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        );

        -- Journal des explications XAI
        CREATE TABLE IF NOT EXISTS xai_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            explanation TEXT,
            factors     TEXT,
            logged_at   DATETIME DEFAULT (datetime('now')),
            FOREIGN KEY (decision_id) REFERENCES decisions(id)
        );

        -- Maladies connues chargées depuis PlantDoc
        CREATE TABLE IF NOT EXISTS plantdoc_diseases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_name  TEXT,
            disease     TEXT,
            symptoms    TEXT,
            treatment   TEXT
        );

    """)

    conn.commit()
    conn.close()
    print("[DB] Base de données initialisée → fellah.db")
