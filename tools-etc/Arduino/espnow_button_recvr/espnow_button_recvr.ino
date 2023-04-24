
#include <esp_now.h>
#include <WiFi.h>

#define LED_PIN   13
#define LED_FLIP_INTERVAL 1000

typedef struct struct_message {
  int button_number;
  int battery_voltage;  
} struct_message;


bool g_flipper = false;
int g_next_led_flip = 0;  // millis


// ---------- setup routines

void setup_espnow() {
  WiFi.mode(WIFI_STA);
  while (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    delay(2000);
  }
  esp_now_register_recv_cb(OnDataRecv);
}

void setup_led() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void setup_serial() {
  Serial.begin(115200);
  while (!Serial) { delay(20); }  // Wait for serial port to stabalize.  
}


// ---------- handlers

void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  const struct_message *myData = (struct_message*) incomingData;
  Serial.printf("button: %d, voltage: %d, mac: ", myData->button_number, myData->battery_voltage);
  for (int i = 0; i < 6; i++) { Serial.print(mac[i], HEX); }
  Serial.println();
}


void handle_serial() {
  if (!Serial.available()) { return; }
  String got = Serial.readString();
  got.trim();
  switch (got.charAt(0)) {
    case '?':  // ping
    case 'p':
      Serial.println("hello!"); 
      break;
    
    case 'b':  // simulate button press
      Serial.printf("button: %d, mac: 00:00:00:00:00:00\n", atoi(got.c_str() + 1));
      break;

    case 'i':  // re-Init espnow
      setup_espnow();
      Serial.println("re-initialized espnow");
      break;
      
    case 'm':  // emit mac address
      Serial.println(WiFi.macAddress());
      break;

    default: 
      Serial.printf("unknown serial command: %s\n", got.c_str());
      break;
  }
}


// ---------- main

void setup() {
  setup_serial();
  setup_led();
  setup_espnow();

  Serial.print("\n\ninit\nMy MAC: "); Serial.println(WiFi.macAddress());
  g_next_led_flip = millis()+ LED_FLIP_INTERVAL;
}


void loop() {
  handle_serial();
  
  // Status update.
  if (millis() >= g_next_led_flip) {
    digitalWrite(LED_PIN, g_flipper);
    g_flipper = !g_flipper;
    g_next_led_flip = millis() + LED_FLIP_INTERVAL;
  }

  // Make sure other cpu events have a chance to run.
  delay(10);
  // yield();
}
