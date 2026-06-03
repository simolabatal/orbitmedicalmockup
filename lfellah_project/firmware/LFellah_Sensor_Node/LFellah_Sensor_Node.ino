/*
 * L'Fellah 2.0 — Arduino Sensor Node v3
 * COM7, 9600 baud
 * Capteurs: DHT22 (D2), TDS (A0), pH (A1), Soil (A2), Relais (D7)
 */

#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int tdsPin = A0;
const int phPin = A1;
const int soilPin = A2;
const int relayPin = 7;

// ─── Calibration pH 2 points ────────────────────────────────────
// Placez la sonde dans buffer pH 4.0 → notez ADC_raw_4
// Placez la sonde dans buffer pH 7.0 → notez ADC_raw_7
// Remplacez les valeurs ci-dessous APRES calibration
const float CAL_PH4_ADC = 478.0;   // ← a mesurer avec buffer pH 4.0
const float CAL_PH7_ADC = 340.0;   // ← a mesurer avec buffer pH 7.0

float calibratePH(float adcRaw) {
  // Calibration lineaire 2 points
  float m = (7.0 - 4.0) / (CAL_PH7_ADC - CAL_PH4_ADC);
  float b = 4.0 - m * CAL_PH4_ADC;
  return constrain(m * adcRaw + b, 0.0, 14.0);
}

// ─── Calibration humidite sol ────────────────────────────────────
const int soilDry = 1023;  // ADC a l'air libre
const int soilWet = 300;   // ADC dans l'eau
const int SOIL_THRESHOLD = 35; // % — seuil declenchement pompe automatique

bool manualOverride = false; // true = commande manuelle active, pas d'auto-off

void setup() {
  Serial.begin(9600);
  dht.begin();
  digitalWrite(relayPin, HIGH); // Anti-bounce: HIGH avant pinMode
  pinMode(relayPin, OUTPUT);

  Serial.println("L'Fellah Node v3 Initialized...");
}

void loop() {
  // ── 1. Lecture DHT22 ──────────────────────────────────────────
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // ── 2. Lecture ADC avec lissage (moyenne 5 lectures) ──────────
  long tdsRaw = 0, phRaw = 0, soilRaw = 0;
  for (int i = 0; i < 5; i++) {
    tdsRaw += analogRead(tdsPin);
    phRaw += analogRead(phPin);
    soilRaw += analogRead(soilPin);
    delay(10);
  }

  float tdsAvg = tdsRaw / 5.0;
  float phAvg = phRaw / 5.0;
  int soilAvg = soilRaw / 5.0;

  // ── 3. Conversion ─────────────────────────────────────────────
  float phValue = calibratePH(phAvg);
  int soilMoisture = map(soilAvg, soilDry, soilWet, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);

  // ── 5. Ecoute commandes relais (bridge → dashboard) ──────────
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "RELAY:ON") {
      digitalWrite(relayPin, LOW);
      manualOverride = true;
      Serial.println("{\"relay\":\"ON\"}");
    } else if (cmd == "RELAY:OFF") {
      digitalWrite(relayPin, HIGH);
      manualOverride = true;  // garde OFF meme si sol sec
      Serial.println("{\"relay\":\"OFF\"}");
    } else if (cmd == "AUTO") {
      manualOverride = false;  // repasser en mode auto
      Serial.println("{\"relay\":\"AUTO\"}");
    } else if (cmd == "STATUS") {
      int state = digitalRead(relayPin);
      Serial.print("{\"relay\":\"");
      Serial.print(state == LOW ? "ON" : "OFF");
      Serial.println("\"}");
    }
  }

  // ── 6. Automatisation pompe — seuil humidite sol ────────────
  if (!manualOverride) {
    if (soilMoisture < SOIL_THRESHOLD) {
      digitalWrite(relayPin, LOW);   // Pompe ON — sol trop sec
    } else {
      digitalWrite(relayPin, HIGH);  // Pompe OFF — humidite OK
    }
  }

  // ── 7. Envoi JSON capteurs (avec etat relais pour sync UI) ──
  int relayState = digitalRead(relayPin);
  Serial.print("{\"temp\":"); Serial.print(isnan(t) ? 0.0 : t);
  Serial.print(", \"hum\":"); Serial.print(isnan(h) ? 0.0 : h);
  Serial.print(", \"tds\":"); Serial.print(tdsAvg);
  Serial.print(", \"ph\":"); Serial.print(phValue, 1);
  Serial.print(", \"phRaw\":"); Serial.print(phAvg, 0);
  Serial.print(", \"soil\":"); Serial.print(soilMoisture);
  Serial.print(", \"relay\":\""); Serial.print(relayState == LOW ? "ON" : "OFF");
  Serial.println("\"}");

  delay(2000);
}