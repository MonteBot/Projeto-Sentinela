#include <Arduino.h>

// ============================================================================
// 1. CONFIGURAÇÃO DE SILÊNCIO E JUMPERS
// ============================================================================
// true = Com os 3 jumpers verdes instalados embaixo dos drivers DRV8825 X e Y (1/32 passo)
// false = Sem jumpers embaixo dos drivers X e Y (passo cheio = 200 passos/volta)
#define USANDO_JUMPERS_MICROSTEP  true

// true = Desenergiza os motores 300ms após parar (zero ruído e zero aquecimento parado)
#define AUTO_SLEEP_PARADO         true

// ============================================================================
// PINAGEM CNC SHIELD V4 (ARDUINO NANO)
// Caso os motores travem mas não girem no autoteste, inverta STEP (2, 3) e DIR (5, 6)
// ============================================================================
#define X_DIR_PIN    2
#define Y_DIR_PIN    3
#define X_STEP_PIN   5
#define Y_STEP_PIN   6
#define ENABLE_PIN   8
#define GATILHO_PIN  A3

#define MASCARA_STEPS ((1 << X_STEP_PIN) | (1 << Y_STEP_PIN))

#if USANDO_JUMPERS_MICROSTEP
  #define PASSOS_POR_VOLTA_X  6400.0f
  #define PASSOS_POR_VOLTA_Y  6400.0f
  #define MAX_SPS_X           1800.0f
  #define MAX_SPS_Y           1400.0f
#else
  #define PASSOS_POR_VOLTA_X  200.0f
  #define PASSOS_POR_VOLTA_Y  200.0f
  #define MAX_SPS_X           180.0f
  #define MAX_SPS_Y           140.0f
#endif

const float PASSOS_POR_GRAU_X = PASSOS_POR_VOLTA_X / 360.0f;
const float PASSOS_POR_GRAU_Y = PASSOS_POR_VOLTA_Y / 360.0f;

#define ANGULO_X_MIN  -135.0f
#define ANGULO_X_MAX   135.0f
#define ANGULO_Y_MIN   -35.0f
#define ANGULO_Y_MAX    45.0f

#define ACELERACAO_X    180.0f
#define ACELERACAO_Y    150.0f
#define TIMER_FREQ      40000UL

volatile uint16_t incX = 0;
volatile uint16_t incY = 0;
volatile int8_t   sentidoX = 1;
volatile int8_t   sentidoY = 1;
volatile int32_t  posPassosX = 0;
volatile int32_t  posPassosY = 0;

int32_t minPassosX, maxPassosX;
int32_t minPassosY, maxPassosY;

bool modoPosicaoAngular = false;
float anguloAlvoX = 0.0f, anguloAlvoY = 0.0f;
float velAlvoX = 0.0f, velAlvoY = 0.0f;
float velAtualX = 0.0f, velAtualY = 0.0f;

unsigned long ultimoComandoMs = 0;
unsigned long ultimoMovimentoMs = 0;
unsigned long ultimoCalculoRampaUs = 0;

char bufferSerial[40];
uint8_t idxBuffer = 0;

ISR(TIMER1_COMPA_vect) {
  PORTD &= ~MASCARA_STEPS;

  static uint16_t acumX = 0;
  static uint16_t acumY = 0;
  uint8_t mascaraPulso = 0;

  if (incX > 0) {
    if ((sentidoX > 0 && posPassosX < maxPassosX) || (sentidoX < 0 && posPassosX > minPassosX)) {
      uint16_t antX = acumX;
      acumX += incX;
      if (acumX < antX) {
        mascaraPulso |= (1 << X_STEP_PIN);
        posPassosX += sentidoX;
      }
    }
  }

  if (incY > 0) {
    if ((sentidoY > 0 && posPassosY < maxPassosY) || (sentidoY < 0 && posPassosY > minPassosY)) {
      uint16_t antY = acumY;
      acumY += incY;
      if (acumY < antY) {
        mascaraPulso |= (1 << Y_STEP_PIN);
        posPassosY += sentidoY;
      }
    }
  }

  if (mascaraPulso) {
    PORTD |= mascaraPulso;
  }
}

void aplicarVelocidadeHardware(float pctX, float pctY) {
  int8_t sX = (pctX >= 0.0f) ? 1 : -1;
  int8_t sY = (pctY >= 0.0f) ? 1 : -1;

  if (sX > 0) PORTD |= (1 << X_DIR_PIN);
  else        PORTD &= ~(1 << X_DIR_PIN);

  if (sY > 0) PORTD |= (1 << Y_DIR_PIN);
  else        PORTD &= ~(1 << Y_DIR_PIN);

  float spsX = (fabs(pctX) / 100.0f) * MAX_SPS_X;
  float spsY = (fabs(pctY) / 100.0f) * MAX_SPS_Y;

  uint16_t novoIncX = (fabs(pctX) < 1.5f) ? 0 : (uint16_t)((spsX * 65536.0f) / TIMER_FREQ);
  uint16_t novoIncY = (fabs(pctY) < 1.5f) ? 0 : (uint16_t)((spsY * 65536.0f) / TIMER_FREQ);

  if (novoIncX > 0 || novoIncY > 0) {
    digitalWrite(ENABLE_PIN, LOW);
    ultimoMovimentoMs = millis();
  } else if (AUTO_SLEEP_PARADO && (millis() - ultimoMovimentoMs > 300)) {
    digitalWrite(ENABLE_PIN, HIGH);
  }

  noInterrupts();
  sentidoX = sX;
  sentidoY = sY;
  incX = novoIncX;
  incY = novoIncY;
  interrupts();
}

void processarComando(char* cmd) {
  if (cmd[0] == 'Z' || cmd[0] == 'z') {
    noInterrupts();
    posPassosX = 0;
    posPassosY = 0;
    interrupts();
    velAlvoX = 0;
    velAlvoY = 0;
    velAtualX = 0;
    velAtualY = 0;
    modoPosicaoAngular = false;
    aplicarVelocidadeHardware(0, 0);
    return;
  }

  if (cmd[0] == 'A' || cmd[0] == 'a') {
    char* p = cmd + 1;
    char* fim = nullptr;
    float ax = (float)strtod(p, &fim);
    if (fim == p) return;
    p = fim;
    float ay = (float)strtod(p, &fim);
    if (fim == p) return;
    int g = (int)strtol(fim, nullptr, 10);

    anguloAlvoX = constrain(ax, ANGULO_X_MIN, ANGULO_X_MAX);
    anguloAlvoY = constrain(ay, ANGULO_Y_MIN, ANGULO_Y_MAX);
    modoPosicaoAngular = true;
    digitalWrite(GATILHO_PIN, (g > 0) ? HIGH : LOW);
    ultimoComandoMs = millis();
    return;
  }

  int vx = 0, vy = 0, g = 0;
  if (sscanf(cmd, "%d %d %d", &vx, &vy, &g) >= 2) {
    modoPosicaoAngular = false;
    velAlvoX = constrain(vx, -100, 100);
    velAlvoY = constrain(vy, -100, 100);
    if (velAlvoX == 0) velAtualX = 0;
    if (velAlvoY == 0) velAtualY = 0;
    digitalWrite(GATILHO_PIN, (g > 0) ? HIGH : LOW);
    ultimoComandoMs = millis();
  }
}

void lerSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (idxBuffer > 0) {
        bufferSerial[idxBuffer] = '\0';
        processarComando(bufferSerial);
        idxBuffer = 0;
      }
    } else if (idxBuffer < sizeof(bufferSerial) - 1) {
      bufferSerial[idxBuffer++] = c;
    }
  }
}

void autotesteSilencioso() {
  digitalWrite(ENABLE_PIN, LOW);
  const unsigned long tMs = 600;
  unsigned long t0 = millis();
  while (millis() - t0 < tMs) {
    float v = sin(((float)(millis() - t0) / tMs) * PI) * 35.0f;
    aplicarVelocidadeHardware(v, v * 0.6f);
    delay(4);
  }
  t0 = millis();
  while (millis() - t0 < tMs) {
    float v = -sin(((float)(millis() - t0) / tMs) * PI) * 35.0f;
    aplicarVelocidadeHardware(v, v * 0.6f);
    delay(4);
  }
  aplicarVelocidadeHardware(0, 0);
  noInterrupts();
  posPassosX = 0;
  posPassosY = 0;
  interrupts();
}

void setup() {
  Serial.begin(115200);

  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(GATILHO_PIN, OUTPUT);

  digitalWrite(ENABLE_PIN, LOW);
  digitalWrite(GATILHO_PIN, LOW);

  minPassosX = (int32_t)(ANGULO_X_MIN * PASSOS_POR_GRAU_X);
  maxPassosX = (int32_t)(ANGULO_X_MAX * PASSOS_POR_GRAU_X);
  minPassosY = (int32_t)(ANGULO_Y_MIN * PASSOS_POR_GRAU_Y);
  maxPassosY = (int32_t)(ANGULO_Y_MAX * PASSOS_POR_GRAU_Y);

  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  OCR1A  = (16000000UL / (8UL * TIMER_FREQ)) - 1; // 49 -> 40 kHz
  TCCR1B |= (1 << WGM12) | (1 << CS11);
  TIMSK1 |= (1 << OCIE1A);
  interrupts();

  delay(300);
  autotesteSilencioso();

  ultimoComandoMs = millis();
  ultimoMovimentoMs = millis();
  ultimoCalculoRampaUs = micros();
}

void loop() {
  lerSerial();

  if (!modoPosicaoAngular && (millis() - ultimoComandoMs > 500)) {
    velAlvoX = 0.0f;
    velAlvoY = 0.0f;
    velAtualX = 0.0f;
    velAtualY = 0.0f;
    digitalWrite(GATILHO_PIN, LOW);
  }

  if (modoPosicaoAngular) {
    noInterrupts();
    int32_t pX = posPassosX;
    int32_t pY = posPassosY;
    interrupts();

    float angAtualX = pX / PASSOS_POR_GRAU_X;
    float angAtualY = pY / PASSOS_POR_GRAU_Y;

    float erroX = anguloAlvoX - angAtualX;
    float erroY = anguloAlvoY - angAtualY;

    velAlvoX = (fabs(erroX) < 0.3f) ? 0.0f : constrain(erroX * 5.0f, -75.0f, 75.0f);
    velAlvoY = (fabs(erroY) < 0.3f) ? 0.0f : constrain(erroY * 5.0f, -60.0f, 60.0f);
    if (velAlvoX == 0.0f && velAlvoY == 0.0f) {
      modoPosicaoAngular = false;
    }
  }

  unsigned long agoraUs = micros();
  if (agoraUs - ultimoCalculoRampaUs >= 2000) {
    float dt = (agoraUs - ultimoCalculoRampaUs) / 1000000.0f;
    ultimoCalculoRampaUs = agoraUs;

    float passoMaxX = ACELERACAO_X * dt;
    float passoMaxY = ACELERACAO_Y * dt;

    if (velAlvoX == 0.0f) velAtualX = 0.0f;
    else if (velAtualX < velAlvoX) velAtualX = min(velAtualX + passoMaxX, velAlvoX);
    else if (velAtualX > velAlvoX) velAtualX = max(velAtualX - passoMaxX, velAlvoX);

    if (velAlvoY == 0.0f) velAtualY = 0.0f;
    else if (velAtualY < velAlvoY) velAtualY = min(velAtualY + passoMaxY, velAlvoY);
    else if (velAtualY > velAlvoY) velAtualY = max(velAtualY - passoMaxY, velAlvoY);

    aplicarVelocidadeHardware(velAtualX, velAtualY);
  }
}
