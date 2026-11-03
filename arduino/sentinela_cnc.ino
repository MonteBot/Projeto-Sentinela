#define X_STEP 2
#define X_DIR  5
#define Y_STEP 3
#define Y_DIR  6
#define ENABLE 8

void setup() {
  Serial.begin(115200);
  pinMode(X_STEP, OUTPUT);
  pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT);
  pinMode(Y_DIR, OUTPUT);
  pinMode(ENABLE, OUTPUT);
  digitalWrite(ENABLE, LOW);
}

void loop() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    int sep = comando.indexOf(' ');
    if (sep != -1) {
      int posX = comando.substring(0, sep).toInt();
      int posY = comando.substring(sep + 1).toInt();
      
      digitalWrite(X_DIR, posX >= 0 ? HIGH : LOW);
      digitalWrite(Y_DIR, posY >= 0 ? HIGH : LOW);
      
      for (int i = 0; i < abs(posX); i++) {
        digitalWrite(X_STEP, HIGH); delayMicroseconds(800);
        digitalWrite(X_STEP, LOW);  delayMicroseconds(800);
      }
      for (int i = 0; i < abs(posY); i++) {
        digitalWrite(Y_STEP, HIGH); delayMicroseconds(800);
        digitalWrite(Y_STEP, LOW);  delayMicroseconds(800);
      }
    }
  }
}
