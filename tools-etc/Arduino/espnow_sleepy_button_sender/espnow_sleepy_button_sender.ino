
/* Send button pushes via espnow, going into deep sleep between events.
 *  
 * If D0 is pressed within a few seconds of startup (or if AUTO_DEBUG), go into "debug mode".
 * This disables the deep sleep feature, and just listens for buttons using the normal loop().
 * This also allows the board to be re-flashed without racing against sleep (which disables the USB port).
 * 
 * In normal (non-debug) mode, board just goes to sleep until woken by a button.  Then sends the
 * button number (and possibly the current battery voltage), waits for an espnow ACK, and goes back to sleep.
 * 
 * For battery voltage to work, A2 should be connected to the battery via a voltage divider (as it is by the
 * qt-py BFF), and USE_A2 should be set to false.
 * 
 * PROD_MODE disables waiting for the serial port to stabalize and turns off most use of the neopixel once
 * the start-up process is complete.  This makes things faster and lowers battery consumption.
 * 
 * Up to 6 pins are supported: A0->A5.  We attempt to activate pulldown resistors in a way that will survive
 * during sleep, but this seems unrelaible on some boards.  So: (a) turn off the USE_A{x} control variables 
 * for any inputs not in use (to prevent false wake/triggering), and (b) use external resistors when false
 * triggers for used pins indicate the need.  NOTE: often it's only individual pins that seem to lose their
 * internal pulldowns;  try moving the input to another pin.
 * 
 * You must trigger HIGH to activate a button (due to esp32 sleep implementation restrictions).
 * 
 * Note that in some cases, the Arduino compiler seems to pull up the wrong pin number constants for some of 
 * the A{x} pins.  No idea why.  To fix this, they are overriden locally with #define's.  The current numbers
 * are set for the QT Py ESP32sX. * 
 * 
 */

#include <Adafruit_NeoPixel.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include "driver/rtc_io.h"


// ---------- control constants

// ----- prod mode

const bool PROD_MODE = true;                       // Don't wait for serial port, lower neopixel usage.


// ----- debug mode

const bool AUTO_DEBUG = false;                     // Enter into debug mode right away, even without D0 push.
const int PWR_ON_DELAY_BEFORE_SLEEP_SECS = 4;      // Give user chance to press D0 to enter debug mode.
const int WAIT_FOR_SERIAL_MS = 1200;               // overridden by PROD_MODE.


// ----- espnow controls

uint8_t recvrAddress[] = {0x24, 0x0A, 0xC4, 0x0D, 0x9E, 0x7C};   // huzzah1
// broadcast addr: {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}

// If the receiver is using *both* WiFi and espnow, it's necessary to send the espnow message 
// on the same channel as the WiFi network for reliable communication.  If the receiver is only
// using espnow, then this isn't necessary and we can save battery and latency by disabling.
const bool MATCH_WIFI_CHANNEL = false;
//
const char* WIFI_SSID = "kds2";  // Used to find channel number of WiFi network, so we can match the channel.

// ----- buttons

#define D0 0   // qt-py-esp32-sX: D0 / gpio0 is the built in button near the usb-C port.

// Locally override any previous definitions of the GPIO BCM pin numbers, as experience has
// shown that the Arduino compiler can get these wrong.
//
#define A0 18
#define A1 17
#define A2 9
#define A3 8
#define A4 7
#define A5 6

const bool USE_A0 = false;
const bool USE_A1 = true;
const bool USE_A2 = false;  // If using a LiPo BFF, leave this turned off to enable battery level monitoring.
const bool USE_A3 = false;
const bool USE_A4 = false;
const bool USE_A5 = false;

// ---------- Neopixel & color constants

#define NEO_PIN PIN_NEOPIXEL

#define BLACK  0x000000
#define BLUE   0x0000ff
#define GREEN  0x00ff00
#define ORANGE 0xffa500
#define PURPLE 0xa020f0
#define RED    0xff0000
#define WHITE  0x808080
#define YELLOW 0xffff00


// ---------- types

typedef struct struct_message {
  int button_number;
  int battery_voltage;  
} struct_message;


// ---------- global state

Adafruit_NeoPixel g_pixels(1, NEO_PIN, NEO_GRB + NEO_KHZ800);
bool g_neo_enabled = false;

bool g_sleepy = true;                   // Disable sleep until espnow ack/nak received.
int g_ext1_bit_mask = 0;                // see setup_pins()

RTC_DATA_ATTR int32_t g_channel = -1;   // channel found by MATCH_WIFI_CHANNEL.  RTC_DATA_ATTR causes it to be remembered across sleep.


// ---------- forward decls

void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status);
void neo(int color, int delay_ms=0);


// ---------- setup routines

int32_t getWiFiChannel(const char *ssid) {
  if (int32_t n = WiFi.scanNetworks()) {
      for (uint8_t i=0; i<n; i++) {
          if (!strcmp(ssid, WiFi.SSID(i).c_str())) {
              return WiFi.channel(i);
  }   }   }
  return 0;
}

void setup_espnow() {
  WiFi.mode(WIFI_STA);

  if (MATCH_WIFI_CHANNEL) {
    // Change channel to match that of the receiver.
    if (g_channel < 0) {
      neo(WHITE);
      g_channel = getWiFiChannel(WIFI_SSID);
      neo(BLACK);
      Serial.printf("discovered wifi is using channel %d\r\n", g_channel);
    }
    Serial.printf("setting esp_now to use channel %d\r\n", g_channel);
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(g_channel, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);
  }
    
  while (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    delay(4000);
  }
  
  esp_now_register_send_cb(OnDataSent);
  
  // Register peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, recvrAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  // Add peer        
  while (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    delay(4000);
  }

  Serial.println("espnow setup ok.");
}

void setup_neo(bool enable=true) {
  g_neo_enabled = enable;
  if (enable) {  
    digitalWrite(NEOPIXEL_POWER, HIGH);
    g_pixels.begin();
    g_pixels.setBrightness(15); // not so bright  
  }
  else {
    digitalWrite(NEOPIXEL_POWER, LOW);
  }
}

void setup_pin(int pin) {
  int mask = 1 << pin;
  // Serial.printf("activating pin %d, mask=0x%x\r\n", pin, mask);
  pinMode(pin, INPUT_PULLDOWN);
  rtc_gpio_pulldown_en((gpio_num_t)pin);
  rtc_gpio_pullup_dis((gpio_num_t)pin);
  g_ext1_bit_mask += mask;
}

void setup_pins() {
  pinMode(D0, INPUT_PULLUP);    // hardwired against ground, so must use pullup mode.
  
  g_ext1_bit_mask = 0;
  if (USE_A0) { setup_pin(A0); }
  if (USE_A1) { setup_pin(A1); }
  if (USE_A2) { setup_pin(A2); }
  if (USE_A3) { setup_pin(A3); }
  if (USE_A4) { setup_pin(A4); }
  if (USE_A5) { setup_pin(A5); }
}

void setup_serial() {
  Serial.begin(115200);
  if (PROD_MODE) { return; }
  
  // Wait up to 1 sec for the serial port to stabalize.
  int stop_ms = millis() + WAIT_FOR_SERIAL_MS;
  while (!Serial && (millis() < stop_ms)) { delay(20); }
}


// ---------- business logic

void neo(int color, int delay_ms) {
  if (g_neo_enabled) {
    g_pixels.fill(color);
    g_pixels.show();
  }
  if (delay_ms > 0) { delay(delay_ms); }
}


void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) { 
    Serial.println("recv'd ok"); 
    neo(GREEN, 800);
  }
  else { 
    Serial.printf("recv'd fail: [%d]\r\n", status);
    neo(PURPLE, 800);
  }
  g_sleepy = true;  // enable going back to sleep now.
}


void send_espnow(int num) {
  int battery = USE_A2 ? -1 : analogRead(A2);
  Serial.printf("\r\nSENDING BUTTON NUMBER: %d, battery: %d\r\n", num, battery);
  g_sleepy = false;  // disable re-sleeping until OnDataSent says its okay.

  struct_message myData;
  myData.button_number = num;
  myData.battery_voltage = battery;
  
  esp_err_t result;       
  while ((result = esp_now_send(recvrAddress, (uint8_t *) &myData, sizeof(myData))) != ESP_OK) {
    Serial.printf("send failed: %d\r\n", result);
    neo(RED, 1000);
  }

  Serial.println("sending sequence done; waiting for ack.");
  neo(WHITE, 300);
}


void sleep(int sleepy_timeout_ms=3000) {
  if (PROD_MODE) { setup_neo(false); }
  
  bool flippy = true;
  int wait_until = millis() + sleepy_timeout_ms;
  while (!g_sleepy && (millis() < wait_until)) {
    if (flippy) { Serial.println("waiting for sleepy..."); }
    neo(flippy ? BLUE : BLACK, 300);
    flippy = !flippy;
  }

  Serial.printf("going to sleep;  wake mask=0x%x\r\n", g_ext1_bit_mask);
  neo(BLACK, 200);
  esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON);  // Leave rtc engaged, so pull up/down resisters stay in-place.
  esp_sleep_enable_ext1_wakeup(g_ext1_bit_mask, ESP_EXT1_WAKEUP_ANY_HIGH);
  esp_deep_sleep_start();    // should not return...
}


bool is_pressed(int button) {
  int pressed_state = (button == D0) ? LOW : HIGH;
  return digitalRead(button) == pressed_state;
}

// Return of -1 indicates timeout.
// Calling with button=-1 searches for a (fixed) list of buttons, otherwise waits for a particular one.
int wait_for_button(int button=-1, int timeout_secs=-1, 
                    int color_start=-1, int color_stop=-1, bool blink=true, int interval_ms=250) {
  bool neo_blink_toggle = true;
  int saw_button = -1;
  Serial.printf("waiting %d seconds for button gpio %d.\r\n", timeout_secs, button);
  
  int time_stop = (timeout_secs >= 0) ? (millis() + 1000 * timeout_secs) : 0;
  while ((time_stop == 0) || (millis() < time_stop)) {
    if (button >= 0) {
      if (is_pressed(button)) { saw_button = button; }
    } else {
      if (is_pressed(D0)) { saw_button = D0; Serial.println("saw D0"); }      
      if (USE_A0 && is_pressed(A0)) { saw_button = A0; Serial.println("saw A0"); }
      if (USE_A1 && is_pressed(A1)) { saw_button = A1; Serial.println("saw A1"); }
      if (USE_A2 && is_pressed(A2)) { saw_button = A2; Serial.println("saw A2"); }
      if (USE_A3 && is_pressed(A3)) { saw_button = A3; Serial.println("saw A3"); }
      if (USE_A4 && is_pressed(A3)) { saw_button = A4; Serial.println("saw A4"); }
      if (USE_A5 && is_pressed(A3)) { saw_button = A5; Serial.println("saw A5"); }
    }
    if (saw_button >= 0) { break; }        
    
    if (color_start >= 0) {
      neo(neo_blink_toggle ? color_start : BLACK);
      neo_blink_toggle = !neo_blink_toggle;
    }
    
    delay(interval_ms);
  }
  
  if (color_stop >= 0) { neo(color_stop); }
  Serial.printf("done waiting.  saw button: %d\r\n", saw_button);
  return saw_button;
}


void wait_for_button_release(int button) {
  if (is_pressed(button)) {
    Serial.printf("waiting for button %d to be released.\r\n", button);
  }
  while (is_pressed(button)) {
    delay(100);
  }
}


// ---------- main
//
// If we return from setup(), we'll enter loop(), which implements debug mode.
// If we make it down to the final sleep() call at the bottom of setup(), we enter deep sleep,
// which will eventually run setup() again once the board wakes up.
//
void setup() {
  setup_serial();
  setup_espnow();
  setup_neo();
  setup_pins();

  // -----

  switch (esp_sleep_get_wakeup_cause()) {
    /* case ESP_SLEEP_WAKEUP_EXT0: 
      Serial.println("woken by ext0");
      break;
    */
    
    case ESP_SLEEP_WAKEUP_EXT1: {
      int waked_by_mask = esp_sleep_get_ext1_wakeup_status();
      Serial.printf("woken by ext1 with mask 0x%x\r\n", waked_by_mask);
      int sent = 0;
      int testbit = 0x01;
      for (int i = 0; i < 32; i++) {
        if (waked_by_mask & testbit) { send_espnow(i); ++sent; }
        testbit <<= 1;
      }
      if (sent == 0) {
        Serial.printf("!! woken by ext1, but mask (0x%x) didnt trigger, so assuming A1\r\n", waked_by_mask);
        send_espnow(A1);
        neo(RED, 500);
      }
      break; }
    
    default:
      // Wake is not from sleep, so must be actual board initialization.
      if (AUTO_DEBUG) { return; }
      
      // Give user a chance to abort sleep sequence.  If they push D0, then enter debug mode.
      int saw_button = wait_for_button(D0, PWR_ON_DELAY_BEFORE_SLEEP_SECS, WHITE, BLACK, true);
      if (saw_button == D0) { return; }  // Enter debug mode via loop().
      break;
  }

  sleep();  // Does not return.
}

 
void loop() {  // This is debug mode.
  wait_for_button_release(D0);  // Wait until debug-mode trigger clears, so it doesn't instantly trigger a button push.
  Serial.println("Entering debug mode...");

  while (1) {  
    int saw_button = wait_for_button(-1, -1, ORANGE, BLACK);
    if (saw_button >= 0) { 
      send_espnow(saw_button);
      delay(750);   // wait for button release
    }
    delay(250); // Never loop too fast.
  }
}
