
// ==================================================================================
// Status LED


// ---------- LED indicators

#define NEO_PIN  ??

void setup_led() {
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  pixels.begin(); // INITIALIZE NeoPixel strip object
  pixels.setBrightness(15); // not so bright  
}


void led(int color, int delay_ms=0) {
  pixels.fill(color);
  pixels.show();
  if (delay_ms > 0) { delay(delay_ms); }
}


// ==================================================================================
// WiFi

#include <WiFi.h>

void setup_wifi() {
  WiFi.mode(WIFI_AP_STA); // (WIFI_STA);
  
  led(YELLOW);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.println("Connecting to WiFi..");
    WiFi.begin(SSID, PASSWD);
    delay(1500);
  }
  led(BLACK);
  Serial.println("Connected to WiFi.");  
}

bool connectivity_check() {
  String dontcare = web_get("jack", 80, "/", false);
  if (LAST_WEB_GET_STATUS != 302) Serial.printf("connectivity check saw %d (expected 302); resp: %s\n", LAST_WEB_GET_STATUS, dontcare);
  return LAST_WEB_GET_STATUS == 302;    // Expect a 302 redirecting to https version.
}

void whoami() {
  Serial.print("\My MAC: "); Serial.println(WiFi.macAddress());
  Serial.print("My IP: "); Serial.println(WiFi.localIP());
  Serial.print("My channel: "); Serial.println(WiFi.channel());
}


// ==================================================================================
// Real time clock

#include <ESP32Time.h>

bool setup_rtc() {
  String time_now_str = web_get("jack", 80, "/time", true);
  int time = atoi(time_now_str.c_str());
  if (time <= 0) {
    Serial.println("failed to retireve time.");
    return false;
  }
  rtc.setTime(time);
  T(); Serial.println("time set.");
  return true;
}


void T() { Serial.print(rtc.getTime("%D %T:: ")); }



// ==================================================================================
// Web client

#include <ArduinoHttpClient.h>


// ---------- web client related

int LAST_WEB_GET_STATUS = -1;
WiFiClient wifi_client;
String web_get_out;
String& web_get(String server, int port, String path, bool send_serial = false) {
  HttpClient client = HttpClient(wifi_client, server, port);
  client.setTimeout(WC_TIMEOUT_MS);
  client.setHttpResponseTimeout(WC_TIMEOUT_MS);
  client.get(path);
  LAST_WEB_GET_STATUS = client.responseStatusCode();
  web_get_out = client.responseBody();
  if (send_serial) {
    T(); Serial.printf("\nweb get %s:%d/%s -> [%d] %s\n", 
           server.c_str(), port, path.c_str(), LAST_WEB_GET_STATUS, web_get_out.c_str());
  }
  return web_get_out;
}


// ==================================================================================
// Web server

#include <WebServer.h>

// ---------- webserver related

String SendHTML(const char* content){
  String ptr = "<!DOCTYPE html> <html>\n";
  ptr += "<head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, user-scalable=no\">\n";
  ptr += "<title>Huzzah</title>\n</head>\n<body>\n";
  ptr += content;
  ptr +="</body>\n</html>\n";
  return ptr;
}

void handle_root() {
  T(); Serial.println("root handler called");
  server.send(200, "text/html", SendHTML("hi there!"));
}

void handle_healthz() {
  T(); Serial.println("/healthz handler: ok");
  server.send(200, "text/plain", "ok");  
}

void setup_webserver() {
  server.on("/", handle_root);
  server.on("/healthz", handle_healthz);
  server.on("/test", handle_test);
  server.onNotFound(handle_404);
  server.begin();
  Serial.println("webserver started");
}


// ==================================================================================
// kAuth

#include <SimpleHOTP.h>          // for sha1.


// kAuth
const String hostname="huzzah1";
const String machine_secret="huzzah1-secret";
const String username = "";
const String password = "";


String sha1_out;
String& sha1(String& in) {
  int ml = in.length(); // message len in bytes
  char temp[ml + 1];
  in.toCharArray(temp, ml + 1);

  ml *= 8;  // now in bits.
  uint32_t hash[5] = {};
  SimpleSHA1::generateSHA((uint8_t*)temp, ml, hash);
  
  sha1_out = "";
  for (int i = 0; i < 5; i++) {
    String tmp = String(hash[i], HEX);
    while (tmp.length() < 8) { tmp = "0" + tmp; }
    sha1_out += tmp;
  }
  sha1_out.toLowerCase();
  return sha1_out;
}

String ss_out;
String& generate_shared_secret(const String hostname, const String machine_priv_data, const String username, const String password) {
  String data_to_hash = hostname + ":" + machine_priv_data + ":" + username + ":" + password;
  String hashed = sha1(data_to_hash);
  ss_out = "SharedSecret(version_tag='v2', hostname='" + hostname + "', username='" + username + "', secret='" + hashed + "', server_override_hostname=None)";
  return ss_out;
}

String token_out;
String& generate_token(const String command, const String hostname, const String machine_priv_data, const String username = "", String password = "") {
  String time_now = String(rtc.getEpoch());
  String plaintext_context = "v2:" + hostname + ":" + username + ":" + time_now;
  String shared_secret = generate_shared_secret(hostname, machine_priv_data, username, password);
  String data_to_hash = plaintext_context + ":" + command + ":" + shared_secret;
  String hashed = sha1(data_to_hash);
  token_out = plaintext_context + ":" + hashed;
  return token_out;
}



// ==================================================================================
// espnow

#include <esp_now.h>


// This is called from a context still involved with the espnow network.
// It breaks both networks to try and make a WiFi call in this context..
//
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  const struct_message *myData = (struct_message*) incomingData;
  // ...
}

void setup_espnow() {
  WiFi.mode(WIFI_AP_STA); // (WIFI_STA);
  while (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    delay(2000);
  }
  esp_now_register_recv_cb(OnDataRecv);
}



