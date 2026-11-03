# 🛡️ Projeto Sentinela - Torreta Autónoma de Defesa

O **Projeto Sentinela** é uma torreta autónoma baseada em **Raspberry Pi** e **Arduino**, projetada para deteção, rastreamento facial e acionamento de um mecanismo de defesa de gel acionado por relé.

## 🚀 Funcionalidades
- **Deteção & Reconhecimento Facial:** Haar Cascade + LBPH (OpenCV).
- **Fail-Safe Tático:** Bloqueio de disparo caso o tronco não esteja visível no enquadramento.
- **Controlo de Movimento:** Arduino Nano + CNC Shield v3 com motores de passo NEMA 17 (`17HS4401S` na base Pan e `17HS4023` no eixo Tilt).
- **Disparo Autónomo:** Módulo Relé (GPIO 22) com bateria externa dedicada.
- **Interface Web Flask:** Transmissão MJPEG ao vivo e telemetria (FPS, estado da trava e disparo).

## 🚦 Como Executar
1. Treinar o modelo: `python3 treinar.py`
2. Iniciar a torreta: `python3 torreta.py`
3. Aceder ao painel: `http://<IP_DO_PI>:5000`
