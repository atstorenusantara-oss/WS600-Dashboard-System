#include <HardwareSerial.h>
#include <ModbusMaster.h>
#include <math.h>
#include <string.h>

// =======================
// PIN CONFIG
// =======================
#define MAX485_DE 4
#define RXD2 16
#define TXD2 17

#define NEXTION_RX 26
#define NEXTION_TX 27

// =======================
// MODBUS CONFIG
// =======================
static const uint8_t SLAVE_ID = 1;
static const uint16_t REGISTER_COUNT = 20;
static const uint16_t START_ADDRESSES[] = {0, 1};
static const uint8_t START_ADDRESS_COUNT = sizeof(START_ADDRESSES) / sizeof(START_ADDRESSES[0]);

static const char* FIELD_NAMES[10] = {
  "Wind Speed",
  "Wind Dir",
  "Temp",
  "Humidity",
  "Pressure",
  "Rain(min)",
  "Rain(hour)",
  "Rain(day)",
  "Rain(total)",
  "Radiation"
};

static const float MIN_RANGE[10] = {
  0.0f, 0.0f, -60.0f, 0.0f, 800.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f
};

static const float MAX_RANGE[10] = {
  80.0f, 360.0f, 80.0f, 100.0f, 1200.0f, 200.0f, 400.0f, 1000.0f, 20000.0f, 2500.0f
};

ModbusMaster node;
HardwareSerial RS485Serial(2);
HardwareSerial nextion(1);

void preTransmission() {
  digitalWrite(MAX485_DE, HIGH);
}

void postTransmission() {
  digitalWrite(MAX485_DE, LOW);
}

float decodeFloat(uint16_t reg1, uint16_t reg2, bool byteBig, bool wordBig) {
  uint16_t wordHigh = wordBig ? reg1 : reg2;
  uint16_t wordLow = wordBig ? reg2 : reg1;

  uint8_t hiMsb = byteBig ? (wordHigh >> 8) : (wordHigh & 0xFF);
  uint8_t hiLsb = byteBig ? (wordHigh & 0xFF) : (wordHigh >> 8);
  uint8_t loMsb = byteBig ? (wordLow >> 8) : (wordLow & 0xFF);
  uint8_t loLsb = byteBig ? (wordLow & 0xFF) : (wordLow >> 8);

  uint32_t bits = ((uint32_t)hiMsb << 24) |
                  ((uint32_t)hiLsb << 16) |
                  ((uint32_t)loMsb << 8) |
                  (uint32_t)loLsb;

  float value;
  memcpy(&value, &bits, sizeof(value));
  return value;
}

void decodeDataset(const uint16_t regs[REGISTER_COUNT], bool byteBig, bool wordBig, float out[10]) {
  for (uint8_t i = 0; i < 10; i++) {
    uint8_t idx = i * 2;
    out[i] = decodeFloat(regs[idx], regs[idx + 1], byteBig, wordBig);
  }
}

int scoreDataset(const float values[10]) {
  int score = 0;
  for (uint8_t i = 0; i < 10; i++) {
    if (isfinite(values[i]) && values[i] >= MIN_RANGE[i] && values[i] <= MAX_RANGE[i]) {
      score++;
    }
  }
  return score;
}

void sendToNextion(const String& component, const String& value) {
  nextion.print(component + ".txt=\"" + value + "\"");
  nextion.write(0xFF);
  nextion.write(0xFF);
  nextion.write(0xFF);
}

void setup() {
  Serial.begin(115200);

  pinMode(MAX485_DE, OUTPUT);
  digitalWrite(MAX485_DE, LOW);

  RS485Serial.begin(9600, SERIAL_8N1, RXD2, TXD2);
  nextion.begin(9600, SERIAL_8N1, NEXTION_RX, NEXTION_TX);

  node.begin(SLAVE_ID, RS485Serial);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  Serial.println("WS-600 Logger Start");
}

void loop() {
  uint16_t regs[REGISTER_COUNT];
  float candidate[10];
  float bestData[10];

  int bestScore = -1;
  bool bestByteBig = true;
  bool bestWordBig = true;
  uint16_t bestAddress = START_ADDRESSES[0];
  bool readOk = false;

  for (uint8_t a = 0; a < START_ADDRESS_COUNT; a++) {
    uint16_t startAddress = START_ADDRESSES[a];
    uint8_t result = node.readHoldingRegisters(startAddress, REGISTER_COUNT);

    if (result != node.ku8MBSuccess) {
      continue;
    }

    readOk = true;

    for (uint8_t i = 0; i < REGISTER_COUNT; i++) {
      regs[i] = node.getResponseBuffer(i);
    }

    for (uint8_t combo = 0; combo < 4; combo++) {
      bool byteBig = (combo & 0x01) == 0;
      bool wordBig = (combo & 0x02) == 0;

      decodeDataset(regs, byteBig, wordBig, candidate);
      int score = scoreDataset(candidate);

      if (score > bestScore) {
        bestScore = score;
        bestByteBig = byteBig;
        bestWordBig = wordBig;
        bestAddress = startAddress;
        for (uint8_t i = 0; i < 10; i++) {
          bestData[i] = candidate[i];
        }
      }
    }
  }

  if (!readOk) {
    Serial.println("Modbus Read Failed");
    delay(2000);
    return;
  }

  Serial.println("===== WS-600 DATA =====");
  Serial.printf("Decode -> addr=%u, byte=%s, word=%s, score=%d/10\n",
                bestAddress,
                bestByteBig ? "big" : "little",
                bestWordBig ? "big" : "little",
                bestScore);
  Serial.printf("%s: %.2f m/s\n", FIELD_NAMES[0], bestData[0]);
  Serial.printf("%s: %.2f deg\n", FIELD_NAMES[1], bestData[1]);
  Serial.printf("%s: %.2f C\n", FIELD_NAMES[2], bestData[2]);
  Serial.printf("%s: %.2f %%\n", FIELD_NAMES[3], bestData[3]);
  Serial.printf("%s: %.2f hPa\n", FIELD_NAMES[4], bestData[4]);
  Serial.printf("%s: %.2f mm\n", FIELD_NAMES[5], bestData[5]);
  Serial.printf("%s: %.2f mm\n", FIELD_NAMES[6], bestData[6]);
  Serial.printf("%s: %.2f mm\n", FIELD_NAMES[7], bestData[7]);
  Serial.printf("%s: %.2f mm\n", FIELD_NAMES[8], bestData[8]);
  Serial.printf("%s: %.2f W/m2\n", FIELD_NAMES[9], bestData[9]);
  Serial.println("========================\n");

  sendToNextion("tWind", String(bestData[0], 1));
  sendToNextion("tTemp", String(bestData[2], 1));
  sendToNextion("tHum", String(bestData[3], 0));
  sendToNextion("tPress", String(bestData[4], 0));
  sendToNextion("tRain", String(bestData[8], 1));
  sendToNextion("tRad", String(bestData[9], 0));

  delay(2000);
}
