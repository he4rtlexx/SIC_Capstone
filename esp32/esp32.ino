#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_SHT31.h>

#define WIFI_SSID ""
#define WIFI_PASS ""
#define MQTT_SERVER ""
#define MQTT_PORT 1883

#define SOIL_PIN 34        
#define PUMP_PIN 27        

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_SHT31 sht31 = Adafruit_SHT31();

String pump_state = "off";
String mode = "manual";

void setup_wifi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected, IP address: ");
  Serial.println(WiFi.localIP());
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String msg = String((char*)payload).substring(0, length);
  if (String(topic) == "farm/pump_control") {
    if (msg == "on") {
      digitalWrite(PUMP_PIN, HIGH);
      pump_state = "on";
    } else if (msg == "off") {
      digitalWrite(PUMP_PIN, LOW);
      pump_state = "off";
    }
  } else if (String(topic) == "farm/mode") {
    mode = msg;
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
      client.subscribe("farm/pump_control");
      client.subscribe("farm/mode");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 1 second");
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);
  setup_wifi();
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(mqtt_callback);
  sht31.begin(0x44);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  float temp = sht31.readTemperature();
  float hum = sht31.readHumidity();
  int soil_raw = analogRead(SOIL_PIN);
  float soil_percent = (4095.0 - soil_raw) / 4095.0 * 100.0;

  if (mode == "auto") {
    if (soil_percent < 20 && pump_state == "off") {
      digitalWrite(PUMP_PIN, HIGH);
      pump_state = "on";
    } else if (soil_percent > 60 && pump_state == "on") {
      digitalWrite(PUMP_PIN, LOW);
      pump_state = "off";
    }
  }

  
  String payload = "{\"temperature\":";
  payload += String(temp, 2);
  payload += ",\"humidity\":";
  payload += String(hum, 2);
  payload += ",\"soil_percent\":";
  payload += String(soil_percent, 2);
  payload += "}";

  client.publish("farm/sensor", payload.c_str());
  client.publish("farm/pump_state", pump_state.c_str());

  Serial.print("Temp: "); Serial.println(temp);
  Serial.print("Humidity: "); Serial.println(hum);
  Serial.print("Soil: "); Serial.println(soil_percent);

  delay(5000); 
}
