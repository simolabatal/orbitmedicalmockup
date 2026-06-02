/*
 * Project: L'Fellah
 * File: LFellah_Sensor_Node.ino
 * Description: Data collection for Hydroponic Sensors & Pump control
 * Wiring: DHT22 (D2), TDS (A0), pH (A1), Relay (D7)
 */

#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int tdsPin = A0;
const int phPin = A1;
const int soilPin = A2;
const int relayPin = 7;

// Calibration humidite sol — a ajuster apres test
const int soilDry   = 1023;  // valeur ADC sol sec (air libre)
const int soilWet   = 300;   // valeur ADC sol humide (dans l'eau)

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, HIGH); 
  
  Serial.println("L'Fellah Node Initialized...");
}

void loop() {
  // Lecture de la température et humidité
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // Lecture du TDS
  int tdsValue = analogRead(tdsPin);
  
  // Lecture et conversion du pH avec logique inversée
  float phRaw = analogRead(phPin);
  float phValue = 14.0 - (phRaw / 73.1);

  // Lecture humidité sol (A2) — calibration a ajuster demain
  int soilRaw = analogRead(soilPin);
  int soilMoisture = map(soilRaw, soilDry, soilWet, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);

  // Envoi des données en JSON
  String json = "{\"temp\":" + String(t) + ", \"hum\":" + String(h) + ", \"tds\":" + String(tdsValue) + ", \"ph\":" + String(phValue, 1) + ", \"soil\":" + String(soilMoisture) + "}";
  Serial.println(json);

  delay(2000); 
}