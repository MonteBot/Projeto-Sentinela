#include <Arduino.h>

// ============================================================================
// 1. CONFIGURAÇÃO DE SILÊNCIO E JUMPERS
// ============================================================================
// true = Com os 3 jumpers instalados embaixo dos drivers DRV8825 X e Y (1/32 passo)
// false = Sem jumpers embaixo dos drivers X e Y (passo cheio = 200 passos/volta)
#define USANDO_JUMPERS_MICROSTEP  true

// true  = Desenergiza os motores 400ms após parar (zero chiado/barulho e zero aquecimento parado)
// false = Mantém as bobinas energizadas parado
#define AUTO_SLEEP_PARADO         true
#define TEMPO_SLEEP_MS            400UL

// ============================================================================
// PINAGEM CNC SHIELD V4 (ARDUINO NANO)
// ============================================================================
#define X_DIR_PIN    2
#define Y_DIR_PIN    3
#define X_STEP_PIN   5
#define Y_STEP_PIN   6
#define ENABLE_PIN   8
#define GATILHO_PIN  A3

#define MASCARA_STEPS ((1 << X_STEP_PIN) | (1 << Y_STEP_PIN))
#define MASCARA_DIRS  ((1 << X_DIR_PIN)  | (1 << Y_DIR_PIN))

#if USANDO_JUMPERS_MICROSTEP
  #define PASSOS_POR_VOLTA_X  6400.0f
  #define PASSOS_POR_VOLTA_Y  6400.0f
  #define MAX_SPS_X           1600.0f
  #define MAX_SPS_Y           1000.0f
#else
  #define PASSOS_POR_VOLTA_X  200.0f
  #define PASSOS_POR_VOLTA_Y  200.0f
  #define MAX_SPS_X           160.0f
  #define MAX_SPS_Y           110.0f
#endif

const float PASSOS_POR_GRAU_X = PASSOS_POR_VOLTA_X / 360.0f;
const float PASSOS_POR_GRAU_Y = PASSOS_POR_VOLTA_Y / 360.0f;

#define ANGULO_X_MIN  -720.0f
#define ANGULO_X_MAX   720.0f
#define ANGULO_Y_MIN  -360.0f
#define ANGULO_Y_MAX   360.0f

// Rampas calibradas para alto torque sem estol (especialmente no 17HS4023 do eixo Y)
#define ACELERACAO_X      150.0f
#define ACELERACAO_Y      110.0f
#define DESACELERACAO_X   240.0f
#define DESACELERACAO_Y   180.0f

// 25 kHz continua acima do limite audível (20 kHz), com +38% de folga na CPU do ATmega328P
#define TIMER_FREQ        25000UL

const float FATOR_INC_X = (MAX_SPS_X * 65536.0f) / (100.0f * (float)TIMER_FREQ);
const float FATOR_INC_Y = (MAX_SPS_Y * 65536.0f) / (100.0f * (float)TIMER_FREQ);

volatile uint16_t incX = 0;
volatile uint16_t incY = 0;
volatile int8_t   sentidoX = 1;
volatile int8_t   sentidoY = 1;
volatile int32_t  posPassosX = 0;
volatile int32_t  posPassosY = 0;

bool modoPosicaoAngular = false;
bool driverEnergizado = false;
float anguloAlvoX = 0.0f, anguloAlvoY = 0.0f;
float velAlvoX = 0.0f, velAlvoY = 0.0f;
float velAtualX = 0.0f, velAtualY = 0.0f;

unsigned long ultimoComandoMs = 0;
unsigned long ultimoMovimentoMs = 0;
unsigned long ultimoWakeMs = 0;
unsigned long ultimoCalculoRampaUs = 0;

char bufferSerial[40];
uint8_t idxBuffer = 0;

// Cache local para evitar noInterrupts() desnecessário quando velocidade não mudou
uint16_t cacheIncX = 0xFFFF;
uint16_t cacheIncY = 0xFFFF;
int8_t   cacheSX   = 0;
int8_t   cacheSY   = 0;

// ============================================================================
// INTERRUPÇÃO DDS DE 25 kHz (ENXUTA E LIVRE DE JITTER)
// ============================================================================
ISR(TIMER1_COMPA_vect) {
  PORTD &= ~MASCARA_STEPS;

  static uint16_t acumX = 0;
  static uint16_t acumY = 0;
  uint8_t mascaraPulso = 0;

  if (incX > 0) {
    uint16_t antX = acumX;
    acumX += incX;
    if (acumX < antX) {
      mascaraPulso |= (1 << X_STEP_PIN);
      posPassosX += sentidoX;
    }
  }

  if (incY > 0) {
    uint16_t antY = acumY;
    acumY += incY;
    if (acumY < antY) {
      mascaraPulso |= (1 << Y_STEP_PIN);
      posPassosY += sentidoY;
    }
  }

  if (mascaraPulso) {
    PORTD |= mascaraPulso;
  }
}

void acordarDrivers() {
  if (!driverEnergizado) {
    digitalWrite(ENABLE_PIN, LOW);
    driverEnergizado = true;
    unsigned long agora = millis();
    ultimoWakeMs = agora;
    ultimoMovimentoMs = agora;
  }
}

// ============================================================================
// APLICAÇÃO DE VELOCIDADE ATÔMICA NO HARDWARE (SEM JITTER QUANDO CONSTANTE)
// ============================================================================
void aplicarVelocidadeHardware(float pctX, float pctY) {
  int8_t sX = (pctX >= 0.0f) ? 1 : -1;
  int8_t sY = (pctY >= 0.0f) ? 1 : -1;

  uint16_t novoIncX = (fabs(pctX) < 1.5f) ? 0 : (uint16_t)(fabs(pctX) * FATOR_INC_X);
  uint16_t novoIncY = (fabs(pctY) < 1.5f) ? 0 : (uint16_t)(fabs(pctY) * FATOR_INC_Y);

  unsigned long agora = millis();
  if (novoIncX > 0 || novoIncY > 0) {
    acordarDrivers();
    ultimoMovimentoMs = agora;
  } else if (AUTO_SLEEP_PARADO && driverEnergizado && (agora - ultimoMovimentoMs > TEMPO_SLEEP_MS)) {
    digitalWrite(ENABLE_PIN, HIGH);
    driverEnergizado = false;
  }

  // Só toca em PORTD e entra em noInterrupts() se passo ou sentido mudarem
  if (novoIncX != cacheIncX || novoIncY != cacheIncY || sX != cacheSX || sY != cacheSY) {
    uint8_t dirs = 0;
    if (sX > 0) dirs |= (1 << X_DIR_PIN);
    if (sY > 0) dirs |= (1 << Y_DIR_PIN);

    noInterrupts();
    PORTD = (PORTD & ~MASCARA_DIRS) | dirs;
    sentidoX = sX;
    sentidoY = sY;
    incX = novoIncX;
    incY = novoIncY;
    interrupts();

    cacheIncX = novoIncX;
    cacheIncY = novoIncY;
    cacheSX   = sX;
    cacheSY   = sY;
  }
}

// ============================================================================
// LEITURA E INTERPRETAÇÃO DOS COMANDOS SERIAIS
// ============================================================================
void processarComando(char* cmd) {
  if (cmd[0] == 'Z' || cmd[0] == 'z') {
    noInterrupts();
    posPassosX = 0;
    posPassosY = 0;
    interrupts();
    velAlvoX = 0.0f;
    velAlvoY = 0.0f;
    velAtualX = 0.0f;
    velAtualY = 0.0f;
    modoPosicaoAngular = false;
    aplicarVelocidadeHardware(0.0f, 0.0f);
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
    velAlvoX = (float)constrain(vx, -100, 100);
    velAlvoY = (float)constrain(vy, -100, 100);
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
  acordarDrivers();
  delay(10);
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
  aplicarVelocidadeHardware(0.0f, 0.0f);
  if (AUTO_SLEEP_PARADO) {
    digitalWrite(ENABLE_PIN, HIGH);
    driverEnergizado = false;
  }
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
  driverEnergizado = true;
  digitalWrite(GATILHO_PIN, LOW);

  noInterrupts();
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1  = 0;
  OCR1A  = (16000000UL / (8UL * TIMER_FREQ)) - 1; // 79 -> 25 kHz
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

  // Watchdog serial: se o cabo USB desconectar ou o script parar (>600ms sem pacotes), freia suavemente
  if (!modoPosicaoAngular && (millis() - ultimoComandoMs > 600)) {
    velAlvoX = 0.0f;
    velAlvoY = 0.0f;
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
  if (agoraUs - ultimoCalculoRampaUs >= 4000) { // 250 Hz de atualização de rampa suave
    float dt = (agoraUs - ultimoCalculoRampaUs) * 0.000001f;
    ultimoCalculoRampaUs = agoraUs;

    // Pré-acorda os drivers alguns milissegundos antes de começar a gerar pulsos
    if (velAlvoX != 0.0f || velAlvoY != 0.0f) {
      bool estavaDormindo = !driverEnergizado;
      acordarDrivers();
      if (estavaDormindo) {
        return;
      }
      if (millis() - ultimoWakeMs < 5) {
        return;
      }
    }

    bool freandoX = (velAlvoX == 0.0f) || ((velAlvoX * velAtualX) < 0.0f) || (fabs(velAlvoX) < fabs(velAtualX));
    bool freandoY = (velAlvoY == 0.0f) || ((velAlvoY * velAtualY) < 0.0f) || (fabs(velAlvoY) < fabs(velAtualY));

    float passoMaxX = (freandoX ? DESACELERACAO_X : ACELERACAO_X) * dt;
    float passoMaxY = (freandoY ? DESACELERACAO_Y : ACELERACAO_Y) * dt;

    if (velAtualX < velAlvoX)      velAtualX = min(velAtualX + passoMaxX, velAlvoX);
    else if (velAtualX > velAlvoX) velAtualX = max(velAtualX - passoMaxX, velAlvoX);

    if (velAtualY < velAlvoY)      velAtualY = min(velAtualY + passoMaxY, velAlvoY);
    else if (velAtualY > velAlvoY) velAtualY = max(velAtualY - passoMaxY, velAlvoY);

    aplicarVelocidadeHardware(velAtualX, velAtualY);
  }
}
