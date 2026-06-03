/*
 * Project: L'Fellah - Node Sensor Corrected
 * Description: Data collection with improved stability & validation
 */

#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int tdsPin = A0;
const int phPin = A1;
const int soilPin = A2;
const int relayPin = 7;

// Calibration : remplacez ces valeurs par celles que vous lisez dans le Serial Monitor (Air / Eau)
const int soilDry = 1023; 
const int soilWet = 300;  

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, HIGH); // Garder la pompe éteinte au démarrage
  
  Serial.println("L'Fellah Node Initialized...");
}

void loop() {
  // 1. Lecture DHT22 avec validation
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // 2. Lecture Analogique avec lissage basique (moyenne de 5 lectures)
  long tdsRaw = 0, phRaw = 0, soilRaw = 0;
  for(int i=0; i<5; i++){
    tdsRaw += analogRead(tdsPin);
    phRaw += analogRead(phPin);
    soilRaw += analogRead(soilPin);
    delay(10);
  }
  
  float tdsAvg = tdsRaw / 5.0;
  float phAvg = phRaw / 5.0;
  int soilAvg = soilRaw / 5.0;

  // 3. Conversion
  float phValue = 14.0 - (phAvg / 73.1); 
  int soilMoisture = map(soilAvg, soilDry, soilWet, 0, 100);
  soilMoisture = constrain(soilMoisture, 0, 100);

  // 4. Envoi JSON propre (avec remplacement de NAN par 0)
  Serial.print("{\"temp\":"); Serial.print(isnan(t) ? 0.0 : t);
  Serial.print(", \"hum\":"); Serial.print(isnan(h) ? 0.0 : h);
  Serial.print(", \"tds\":"); Serial.print(tdsAvg);
  Serial.print(", \"ph\":"); Serial.print(phValue, 1);
  Serial.print(", \"soil\":"); Serial.print(soilMoisture);
  Serial.println("}");

  delay(2000); 
}