/*
 * =====================================================================
 *  SISTEMA DE CONTROLE DA TORRETA (CNC SHIELD V4 + DRV8825 + NANO)
 * =====================================================================
 *  Comandos recebidos via Serial (115200 baud):
 *    'w' -> Eixo Y Cima
 *    's' -> Eixo Y Baixo
 *    'a' -> Eixo X Esquerda
 *    'd' -> Eixo X Direita
 *    'c' -> Liga / Desliga Giro Continuo
 *    'm' -> Alterna Mapeamento de Pinos (D2/D3 vs D5/D6)
 *    '+' -> Aumenta velocidade
 *    '-' -> Diminui velocidade
 *    'e' -> Habilita / Desabilita bobinas (soltar motores)
 * =====================================================================
 */

const int PIN_EN = 8;
const int PIN_LED = 13;

// Pinos Shield V4
const int P2 = 2;
const int P3 = 3;
const int P4 = 4;
const int P5 = 5;
const int P6 = 6;
const int P7 = 7;

// Modo de pinos: false = Padrao (D2/D3 STEP), true = Clone V4 (D5/D6 STEP)
bool pinCloneMode = false;

// Estado dos motores
bool driversEnabled = true;
bool continuousMode = false;
bool contXDir = true;
bool contYDir = true;

// Velocidade (delay entre pulsos de passo em microsegundos)
int stepDelayUs = 1000;

// Quantidade de passos por toque de direcao (400 passos)
int jogSteps = 400;

int getXStepPin() { return pinCloneMode ? P5 : P2; }
int getXDirPin()  { return pinCloneMode ? P2 : P5; }

int getYStepPin() { return pinCloneMode ? P6 : P3; }
int getYDirPin()  { return pinCloneMode ? P3 : P6; }

void setDrivers(bool enable) {
  driversEnabled = enable;
  digitalWrite(PIN_EN, enable ? LOW : HIGH);
  if (enable) {
    Serial.println(F("[DRV] HABILITADO (Bobinas energizadas)"));
  } else {
    Serial.println(F("[DRV] DESABILITADO (Motores livres / soltos)"));
  }
}

void printMode() {
  Serial.print(F("[MAPA PINOS] Modo: "));
  if (!pinCloneMode) {
    Serial.println(F("PADRAO (X_STEP=D2, DIR=D5 | Y_STEP=D3, DIR=D6)"));
  } else {
    Serial.println(F("CLONE V4 INVERTIDO (X_STEP=D5, DIR=D2 | Y_STEP=D6, DIR=D3)"));
  }
}

void stepMotor(int stepPin, int dirPin, bool dir, int steps) {
  if (!driversEnabled) setDrivers(true);

  digitalWrite(dirPin, dir ? HIGH : LOW);
  delayMicroseconds(20);

  for (int i = 0; i < steps; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(stepDelayUs / 2);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(stepDelayUs / 2);
  }
}

void printHelp() {
  Serial.println(F("\n=========================================="));
  Serial.println(F("  PAINEL DE CONTROLE - TORRETA CNC SHIELD "));
  Serial.println(F("=========================================="));
  Serial.println(F("Comandos:"));
  Serial.println(F("  'w' -> Eixo Y para CIMA"));
  Serial.println(F("  's' -> Eixo Y para BAIXO"));
  Serial.println(F("  'a' -> Eixo X para ESQUERDA"));
  Serial.println(F("  'd' -> Eixo X para DIREITA"));
  Serial.println(F("  'c' -> Alterna Giro Continuo"));
  Serial.println(F("  'm' -> Alterna Pinos (Padrao D2/D3 <-> Clone D5/D6)"));
  Serial.println(F("  '+' -> Aumenta velocidade"));
  Serial.println(F("  '-' -> Diminui velocidade"));
  Serial.println(F("  'e' -> Ligar / Desligar Drivers (soltar motor)"));
  Serial.println(F("  'h' -> Exibir este menu de ajuda"));
  printMode();
  Serial.print(F("Velocidade atual: "));
  Serial.print(stepDelayUs);
  Serial.println(F(" us/passo"));
  Serial.println(F("==========================================\n"));
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_EN, OUTPUT);
  pinMode(P2, OUTPUT);
  pinMode(P3, OUTPUT);
  pinMode(P4, OUTPUT);
  pinMode(P5, OUTPUT);
  pinMode(P6, OUTPUT);
  pinMode(P7, OUTPUT);

  digitalWrite(P2, LOW);
  digitalWrite(P3, LOW);
  digitalWrite(P4, LOW);
  digitalWrite(P5, LOW);
  digitalWrite(P6, LOW);
  digitalWrite(P7, LOW);

  setDrivers(true);
  digitalWrite(PIN_LED, HIGH);

  printHelp();
}

void loop() {
  // 1. Se giro continuo estiver ativo
  if (continuousMode && driversEnabled) {
    int xStep = getXStepPin();
    int xDir  = getXDirPin();
    int yStep = getYStepPin();
    int yDir  = getYDirPin();

    digitalWrite(xDir, contXDir ? HIGH : LOW);
    digitalWrite(yDir, contYDir ? HIGH : LOW);

    digitalWrite(xStep, HIGH);
    digitalWrite(yStep, HIGH);
    delayMicroseconds(stepDelayUs / 2);
    digitalWrite(xStep, LOW);
    digitalWrite(yStep, LOW);
    delayMicroseconds(stepDelayUs / 2);
  }

  // 2. Leitura de comandos da Serial
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '\r' || cmd == '\n' || cmd == ' ') return;

    switch (cmd) {
      case 'a':
      case 'A':
        continuousMode = false;
        Serial.println(F(">> Movendo X para ESQUERDA..."));
        stepMotor(getXStepPin(), getXDirPin(), false, jogSteps);
        break;

      case 'd':
      case 'D':
        continuousMode = false;
        Serial.println(F(">> Movendo X para DIREITA..."));
        stepMotor(getXStepPin(), getXDirPin(), true, jogSteps);
        break;

      case 'w':
      case 'W':
        continuousMode = false;
        Serial.println(F(">> Movendo Y para CIMA..."));
        stepMotor(getYStepPin(), getYDirPin(), true, jogSteps);
        break;

      case 's':
      case 'S':
        continuousMode = false;
        Serial.println(F(">> Movendo Y para BAIXO..."));
        stepMotor(getYStepPin(), getYDirPin(), false, jogSteps);
        break;

      case 'c':
      case 'C':
        continuousMode = !continuousMode;
        if (continuousMode) {
          Serial.println(F(">> Giro continuo ATIVADO!"));
        } else {
          Serial.println(F(">> Giro continuo DESATIVADO."));
        }
        break;

      case 'm':
      case 'M':
        pinCloneMode = !pinCloneMode;
        printMode();
        break;

      case 'e':
      case 'E':
        setDrivers(!driversEnabled);
        break;

      case '+':
        if (stepDelayUs > 200) {
          stepDelayUs -= 100;
          Serial.print(F(">> Velocidade Aumentada: "));
          Serial.print(stepDelayUs);
          Serial.println(F(" us"));
        }
        break;

      case '-':
        if (stepDelayUs < 4000) {
          stepDelayUs += 150;
          Serial.print(F(">> Velocidade Diminuida: "));
          Serial.print(stepDelayUs);
          Serial.println(F(" us"));
        }
        break;

      case 'h':
      case '?':
        printHelp();
        break;

      default:
        break;
    }
  }
}
