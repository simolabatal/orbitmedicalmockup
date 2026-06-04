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
const int SOIL_THRESHOLD = 45; // % — seuil declenchement pompe automatique

bool modeAuto = true;  // true = automatique, false = manuel (bouton Dashboard)

// ─── Irrigation Automatique (capteurs + seuil humidité) ──────────
void irrigationAutomatique() {
  // ── 2. Lecture DHT22 ──────────────────────────────────────────
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // ── 3. Lecture ADC avec lissage (moyenne 5 lectures) ──────────
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

  // ── 4. Conversion ─────────────────────────────────────────────
  float phValue = calibratePH(phAvg);
  int soilMoisture = map(soilAvg, soilDry, soilWet, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);

  // ── 5. Automatisation pompe — seuil humidite sol ────────────
  if (soilMoisture < 45) {
    digitalWrite(relayPin, LOW);   // Pompe ON — sol trop sec
  } else {
    digitalWrite(relayPin, HIGH);  // Pompe OFF — humidite OK
  }

  // ── 6. Envoi JSON capteurs ──
  int relayState = digitalRead(relayPin);
  Serial.print("{\"temp\":"); Serial.print(isnan(t) ? 0.0 : t);
  Serial.print(", \"hum\":"); Serial.print(isnan(h) ? 0.0 : h);
  Serial.print(", \"tds\":"); Serial.print(tdsAvg);
  Serial.print(", \"ph\":"); Serial.print(phValue, 1);
  Serial.print(", \"phRaw\":"); Serial.print(phAvg, 0);
  Serial.print(", \"soil\":"); Serial.print(soilMoisture);
  Serial.print(", \"relay\":\""); Serial.print(relayState == LOW ? "ON" : "OFF");
  Serial.print("\", \"mode\":\"AUTO");
  Serial.println("\"}");

  delay(2000);
}

// ─── Irrigation Manuelle (bouton Dashboard) ──────────────────────
void irrigationManuelle() {
  static bool manualOverride = false;
  static unsigned long manualStartTime = 0;
  bool cmdReceived = false;

  // ── 1. Écoute commandes relais ─────────────────────────────────
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "RELAY:ON") {
      digitalWrite(relayPin, LOW);
      manualOverride = true;
      manualStartTime = millis();
      cmdReceived = true;
    } else if (cmd == "RELAY:OFF") {
      digitalWrite(relayPin, HIGH);
      manualOverride = true;
      manualStartTime = millis();
      cmdReceived = true;
    } else if (cmd == "AUTO") {
      manualOverride = false;
      cmdReceived = true;
    } else if (cmd == "STATUS") {
      cmdReceived = true;
    }
  }

  // ── Feedback immédiat après commande ────────────────────────────
  if (cmdReceived) {
    int state = digitalRead(relayPin);
    Serial.print("{\"relay\":\"");
    Serial.print(state == LOW ? "ON" : "OFF");
    Serial.print("\", \"mode\":\"");
    Serial.print(manualOverride ? "MANUAL" : "AUTO");
    Serial.println("\"}");
  }

  // ── Sécurité timeout ────────────────────────────────────────────
  if (manualOverride && (millis() - manualStartTime > 300000)) {
    manualOverride = false;
  }

  // ── Lecture DHT22 ──────────────────────────────────────────
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // ── Lecture ADC avec lissage ────────────────────────────────
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

  // ── Conversion ─────────────────────────────────────────────
  float phValue = calibratePH(phAvg);
  int soilMoisture = map(soilAvg, soilDry, soilWet, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);

  // ── Automatisation pompe — seulement si pas de forçage manuel ──
  if (!manualOverride) {
    if (soilMoisture < 45) {
      digitalWrite(relayPin, LOW);
    } else {
      digitalWrite(relayPin, HIGH);
    }
  }

  // ── Envoi JSON périodique ──
  int relayState = digitalRead(relayPin);
  Serial.print("{\"temp\":"); Serial.print(isnan(t) ? 0.0 : t);
  Serial.print(", \"hum\":"); Serial.print(isnan(h) ? 0.0 : h);
  Serial.print(", \"tds\":"); Serial.print(tdsAvg);
  Serial.print(", \"ph\":"); Serial.print(phValue, 1);
  Serial.print(", \"phRaw\":"); Serial.print(phAvg, 0);
  Serial.print(", \"soil\":"); Serial.print(soilMoisture);
  Serial.print(", \"relay\":\""); Serial.print(relayState == LOW ? "ON" : "OFF");
  Serial.print("\", \"mode\":\"MANUAL");
  Serial.println("\"}");

  delay(2000);
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  digitalWrite(relayPin, HIGH); // Anti-bounce: HIGH avant pinMode
  pinMode(relayPin, OUTPUT);

  Serial.println("L'Fellah Node v3 Initialized...");
}

void loop() {
  // ── Basculement mode Auto/Manuel via caractère simple ──────────
  if (Serial.available() > 0) {
    char c = Serial.peek();
    if (c == 'A') {
      Serial.read();
      while (Serial.available() && Serial.peek() == '\n') { Serial.read(); }
      modeAuto = true;
    } else if (c == 'M') {
      Serial.read();
      while (Serial.available() && Serial.peek() == '\n') { Serial.read(); }
      modeAuto = false;
    }
  }

  if (modeAuto) {
    irrigationAutomatique();
  } else {
    irrigationManuelle();
  }
}