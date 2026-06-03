/*
 * L'Fellah 2.0 — ESP32-CAM Image Uploader
 * Capture photo + envoi HTTP POST vers Django /api/upload/
 *
 * Reseau : ROTATED — Remplacez par votre SSID/mdp
 */

#include "esp_camera.h"
#include "WiFi.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_client.h"

// ─── CONFIG RESEAU — ROTATED, remplacez avant flash ──────────────
const char* ssid      = "YOUR_SSID";
const char* password  = "YOUR_PASSWORD";
const char* serverUrl = "http://192.168.X.X:8000/api/upload/";

// ─── CONFIG CAMERA (AI-THINKER) ─────────────────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define FLASH_LED_PIN      4

// ─── CONNEXION WIFI AVEC DEBUG DETAILLE ─────────────────────────
void connectWiFi() {
  Serial.println();
  Serial.println("══════════════════════════════════════");
  Serial.println("  L'FELLAH ESP32-CAM — Connexion WiFi");
  Serial.println("══════════════════════════════════════");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("[WiFi] SSID cible : ");
  Serial.println(ssid);
  Serial.print("[WiFi] Adresse IP souhaitee : ");
  Serial.println(serverUrl);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    attempts++;
    Serial.print("[WiFi] Tentative ");
    Serial.print(attempts);
    Serial.print("/30 — Statut : ");

    switch (WiFi.status()) {
      case WL_IDLE_STATUS:      Serial.println("IDLE"); break;
      case WL_NO_SSID_AVAIL:    Serial.println("SSID INTROUVABLE"); break;
      case WL_SCAN_COMPLETED:   Serial.println("SCAN OK"); break;
      case WL_CONNECTED:        Serial.println("CONNECTE"); break;
      case WL_CONNECT_FAILED:   Serial.println("ECHEC CONNEXION"); break;
      case WL_CONNECTION_LOST:  Serial.println("CONNEXION PERDUE"); break;
      case WL_DISCONNECTED:     Serial.println("DECONNECTE"); break;
      default: Serial.print("CODE "); Serial.println(WiFi.status());
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("══════════════════════════════════════");
    Serial.println("  [WiFi] ✓ CONNECTE !");
    Serial.print("  IP locale  : ");
    Serial.println(WiFi.localIP());
    Serial.print("  Passerelle : ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("  RSSI       : ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println("══════════════════════════════════════");
  } else {
    Serial.println("══════════════════════════════════════");
    Serial.println("  [WiFi] ✗ ECHEC — Redemarrage...");
    Serial.println("══════════════════════════════════════");
    delay(3000);
    ESP.restart();
  }
}

// ─── SETUP ──────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);

  // Desactiver la detection de brownout (stabilite flash LED)
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  // LED flash en sortie
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  connectWiFi();

  // Config camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;     // 640x480
  config.jpeg_quality = 15;             // 0-63, plus bas = meilleure qualite
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] ✗ Echec init camera : 0x%x\n", err);
    return;
  }
  Serial.println("[CAM] ✓ Camera initialisee");

  // Parametres camera supplementaires
  sensor_t* s = esp_camera_sensor_get();
  s->set_brightness(s, 1);     // -2 a 2
  s->set_contrast(s, 1);       // -2 a 2
  s->set_saturation(s, 0);     // -2 a 2
  s->set_whitebal(s, 1);       // 0 = off, 1 = on
  s->set_awb_gain(s, 1);       // 0 = off, 1 = on
  s->set_wb_mode(s, 0);        // 0 a 4
  s->set_exposure_ctrl(s, 1);  // 0 = off, 1 = on
  s->set_aec2(s, 0);           // 0 = off, 1 = on
  s->set_gain_ctrl(s, 1);      // 0 = off, 1 = on
  s->set_agc_gain(s, 0);       // 0 a 30
  s->set_gainceiling(s, (gainceiling_t)0);
  s->set_quality(s, 15);
  s->set_framesize(s, FRAMESIZE_VGA);

  Serial.println("[READY] En attente de commande photo...");
}

// ─── CAPTURE + ENVOI HTTP POST ──────────────────────────────────
void captureAndUpload() {
  Serial.println("[CAM] Capture en cours...");

  // Activer flash LED
  digitalWrite(FLASH_LED_PIN, HIGH);
  delay(100);

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM] ✗ Echec capture");
    digitalWrite(FLASH_LED_PIN, LOW);
    return;
  }

  digitalWrite(FLASH_LED_PIN, LOW);
  Serial.printf("[CAM] ✓ Photo capturee : %zu octets\n", fb->len);

  // Envoi HTTP POST multipart
  esp_http_client_config_t httpConfig = {};
  httpConfig.url = serverUrl;
  httpConfig.method = HTTP_METHOD_POST;
  httpConfig.timeout_ms = 15000;

  esp_http_client_handle_t client = esp_http_client_init(&httpConfig);
  esp_http_client_set_header(client, "Content-Type", "image/jpeg");
  esp_http_client_set_post_field(client, (const char*)fb->buf, fb->len);

  esp_err_t err = esp_http_client_perform(client);
  if (err == ESP_OK) {
    int status = esp_http_client_get_status_code(client);
    Serial.printf("[HTTP] ✓ Serveur repond : %d\n", status);
  } else {
    Serial.printf("[HTTP] ✗ Erreur envoi : %s\n", esp_err_to_name(err));
  }

  esp_http_client_cleanup(client);
  esp_camera_fb_return(fb);
  Serial.println("[READY] Pret pour la prochaine photo.");
}

// ─── LOOP ───────────────────────────────────────────────────────
void loop() {
  // Verifier la connexion WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] ! Deconnecte — reconnexion...");
    connectWiFi();
  }

  // Capturer et uploader toutes les 10 secondes
  captureAndUpload();
  delay(10000);
}
