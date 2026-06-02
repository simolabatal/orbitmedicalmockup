# =============================================================
#  database/queries.py — Toutes les requêtes SQL du projet
# =============================================================

from .db_manager import get_connection


# ─────────────────────────────────────────────
#  PLANTS
# ─────────────────────────────────────────────

def add_plant(name: str, species: str, location: str,
              target_humidity: float = 60.0,
              target_temp: float = 22.0) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO plants (name, species, location, target_humidity, target_temp)
        VALUES (?, ?, ?, ?, ?)
    """, (name, species, location, target_humidity, target_temp))
    plant_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plant_id


def get_all_plants() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM plants").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_plant(plant_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM plants WHERE id = ?", (plant_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  SENSOR READINGS
# ─────────────────────────────────────────────

def insert_reading(plant_id: int, temperature: float,
                   humidity: float, ph: float,
                   light_lux: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_readings
            (plant_id, temperature, humidity, ph, light_lux)
        VALUES (?, ?, ?, ?, ?)
    """, (plant_id, temperature, humidity, ph, light_lux))
    reading_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reading_id


def get_last_reading(plant_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM sensor_readings
        WHERE plant_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (plant_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_reading_history(plant_id: int, limit: int = 50) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM sensor_readings
        WHERE plant_id = ?
        ORDER BY timestamp DESC LIMIT ?
    """, (plant_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_avg_readings(plant_id: int, last_n: int = 10) -> dict:
    """Moyenne des N dernières lectures — utilisée par le Digital Twin."""
    conn = get_connection()
    row = conn.execute("""
        SELECT
            AVG(temperature) AS avg_temp,
            AVG(humidity)    AS avg_humidity,
            AVG(ph)          AS avg_ph,
            AVG(light_lux)   AS avg_lux
        FROM (
            SELECT temperature, humidity, ph, light_lux
            FROM sensor_readings
            WHERE plant_id = ?
            ORDER BY timestamp DESC LIMIT ?
        )
    """, (plant_id, last_n)).fetchone()
    conn.close()
    return dict(row) if row else {}


# ─────────────────────────────────────────────
#  PLANT IMAGES (vision IA)
# ─────────────────────────────────────────────

def insert_image_result(plant_id: int, image_path: str,
                        stress_label: str, confidence: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO plant_images (plant_id, image_path, stress_label, confidence)
        VALUES (?, ?, ?, ?)
    """, (plant_id, image_path, stress_label, confidence))
    img_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return img_id


def get_last_image_result(plant_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM plant_images
        WHERE plant_id = ?
        ORDER BY captured_at DESC LIMIT 1
    """, (plant_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  TRUST SCORES
# ─────────────────────────────────────────────

def insert_trust_score(reading_id: int, sensor_type: str,
                       score: float, anomaly_reason: str = None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO trust_scores
            (reading_id, sensor_type, score, anomaly_reason)
        VALUES (?, ?, ?, ?)
    """, (reading_id, sensor_type, score, anomaly_reason))
    conn.commit()
    conn.close()


def get_low_trust_sensors(threshold: float = 0.5) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT ts.*, sr.plant_id, sr.timestamp
        FROM trust_scores ts
        JOIN sensor_readings sr ON ts.reading_id = sr.id
        WHERE ts.score < ?
        ORDER BY ts.evaluated_at DESC
    """, (threshold,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  DECISIONS
# ─────────────────────────────────────────────

def insert_decision(plant_id: int, action_type: str,
                    explanation: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO decisions (plant_id, action_type, explanation)
        VALUES (?, ?, ?)
    """, (plant_id, action_type, explanation))
    decision_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return decision_id


def mark_decision_executed(decision_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE decisions SET executed = 1 WHERE id = ?",
        (decision_id,)
    )
    conn.commit()
    conn.close()


def get_decision_history(plant_id: int, limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM decisions
        WHERE plant_id = ?
        ORDER BY decided_at DESC LIMIT ?
    """, (plant_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  DIGITAL TWIN SIMULATIONS
# ─────────────────────────────────────────────

def insert_simulation(decision_id: int, simulated_state: str,
                      is_safe: bool, risk_score: float):
    conn = get_connection()
    conn.execute("""
        INSERT INTO digital_twin_sims
            (decision_id, simulated_state, is_safe, risk_score)
        VALUES (?, ?, ?, ?)
    """, (decision_id, simulated_state, int(is_safe), risk_score))
    conn.commit()
    conn.close()


def get_simulation(decision_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM digital_twin_sims WHERE decision_id = ?
    """, (decision_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  XAI LOGS
# ─────────────────────────────────────────────

def insert_xai_log(decision_id: int, explanation: str, factors: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO xai_logs (decision_id, explanation, factors)
        VALUES (?, ?, ?)
    """, (decision_id, explanation, factors))
    conn.commit()
    conn.close()


def get_xai_log(decision_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM xai_logs WHERE decision_id = ?", (decision_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  PLANTDOC DISEASES
# ─────────────────────────────────────────────

def insert_disease(plant_name: str, disease: str,
                   symptoms: str, treatment: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO plantdoc_diseases
            (plant_name, disease, symptoms, treatment)
        VALUES (?, ?, ?, ?)
    """, (plant_name, disease, symptoms, treatment))
    conn.commit()
    conn.close()


def get_disease_info(disease_name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM plantdoc_diseases
        WHERE disease LIKE ?
        LIMIT 1
    """, (f"%{disease_name}%",)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_diseases() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM plantdoc_diseases").fetchall()
    conn.close()
    return [dict(r) for r in rows]
