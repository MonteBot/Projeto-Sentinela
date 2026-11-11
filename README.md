# Projeto Sentinela — MonteBot

Sistema de torreta sentinela automatizada de 2 eixos (Pan/Tilt) com visão computacional em tempo real, reconhecimento facial (LBPH), telemetria de FPS ao vivo e trava de segurança em 4 camadas para disparo exclusivo na região do tórax.

Desenvolvido por **Henrique Eugênio dos Santos** — Membro do **MonteBot** e **LINA** | Sistemas de Informação — **Universidade Federal de Uberlândia (UFU)**.

---

## 🏗️ Como Funciona (Arquitetura Modular)

O processamento de visão e a geração de pulsos de alta frequência foram desacoplados entre dois sistemas dedicados:

* **Raspberry Pi (Visão Computacional e Painel Web — pasta `torreta/`):**
  * [`app.py`](torreta/app.py): Servidor Flask na porta `5000` com auto-limpeza de processos anteriores (`liberar_instancia_anterior`), stream MJPEG e rotas de controle/telemetria.
  * [`visao.py`](torreta/visao.py): Captura assíncrona OpenCV (`320x240`), medição contínua de **FPS real** (filtro EMA), entrega de frames com latência zero (`threading.Condition`), detecção Haar Cascade, reconhecimento de alvos via **LBPH** com cache em `blacklist/modelo_alvo.yml` e **trava de segurança em 4 camadas** (`ROSTO [PROTEGIDO]`).
  * [`serial_comm.py`](torreta/serial_comm.py): Thread dedicada de comunicação serial (`115200` baud) com reconexão automática, controle de sequência (`seq`), auto-parada manual (`350 ms`) e bloqueio físico do gatilho quando a trava de rosto está ativa.
  * [`config.py`](torreta/config.py): Centralização de parâmetros de câmera, ganhos proporcionais (`KP_X`, `KP_Y`), zona morta e fator de descida para o peito (`FATOR_DESCIDA_PEITO = 1.85`).
  * [`templates/index.html`](torreta/templates/index.html): Painel de controle com indicador de **FPS** ao vivo, cadastro de Blacklist (upload ou captura direta da câmera) e suporte simultâneo a **Gamepad API**, **Teclado** (`WASD`/Setas + `Espaço`) e **D-Pad Touch/Mouse**.

* **Arduino Nano + CNC Shield V4 (Controle de Motores e Disparo — pasta `sentinela_nano_silencioso/`):**
  * [`sentinela_nano_silencioso.ino`](sentinela_nano_silencioso/sentinela_nano_silencioso.ino): Geração de pulsos `STEP` por interrupção de hardware (`Timer1` em modo CTC a `40 kHz`) com acumulador de fase de 16 bits, rampa de aceleração suave, parada instantânea ao zerar comando, *auto-sleep* no pino `ENABLE` (`D8`) após `300 ms` parado e watchdog de segurança de `500 ms`.

---

## ⚙️ Hardware e Pinagem (CNC Shield V4)

* **Processamento e Visão:** Raspberry Pi + Webcam USB
* **Controlador de Motores:** Arduino Nano acoplado na **CNC Shield V4**
* **Drivers de Passo:** 2x **DRV8825** nos slots X e Y com os 3 jumpers verdes sob os drivers (`1/32` micropasso = `6400` passos/volta)
* **Motores NEMA 17 (Usongshine):**
  * **Eixo X (Base / Pan):** `17HS4401S`
  * **Eixo Y (Inclinação / Tilt):** `17HS4023` (*pancake*)
* **Mecanismo de Disparo:** Gearbox elétrica de bolinhas de gel acionada via módulo Relé 5V / MOSFET no pino **`A3`**

| Função | Pino no Arduino Nano (CNC Shield V4) | Observação |
|---|---|---|
| `X_DIR_PIN` | `D2` | Direção Pan (Base) |
| `Y_DIR_PIN` | `D3` | Direção Tilt (Inclinação) |
| `X_STEP_PIN` | `D5` | Pulso Step Pan |
| `Y_STEP_PIN` | `D6` | Pulso Step Tilt |
| `ENABLE_PIN` | `D8` | Ativo em `LOW` (*auto-sleep* em `HIGH` 300ms após parar) |
| `GATILHO_PIN` | `A3` | Relé / MOSFET da Gearbox |

---

## 🚀 Instalação e Execução

1. **Instalar dependências no Raspberry Pi:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Gravar o firmware no Arduino Nano:**
   Abra [`sentinela_nano_silencioso/sentinela_nano_silencioso.ino`](sentinela_nano_silencioso/sentinela_nano_silencioso.ino) na Arduino IDE e faça o upload para o Arduino Nano (`ATmega328P`).

3. **Iniciar o servidor no Raspberry Pi:**
   ```bash
   cd torreta
   python3 app.py
   ```

4. **Acesso ao Painel Web:**
   Abra no navegador: `http://<IP_DO_RASPBERRY>:5000`

---

## 📅 Cronograma e Status do Projeto

### Fase 1: Software e Repositório (Concluído)
* [x] Arquitetura modular de visão computacional e servidor (`app.py`, `visao.py`, `serial_comm.py`, `config.py`)
* [x] Firmware silencioso em `Timer1` (`40 kHz`) para CNC Shield V4 + DRV8825 `1/32` (`sentinela_nano_silencioso.ino`)
* [x] Reconhecimento facial LBPH com variações sintéticas e cadastro de Blacklist em tempo real
* [x] Trava de segurança em 4 camadas para mira e disparo exclusivos no tórax (`ROSTO [PROTEGIDO]`)
* [x] Painel Web com FPS em tempo real, Gamepad API, teclado e D-Pad touch

### Fase 2: Hardware e Testes Físicos (Concluído / Em Operação)
* [x] Montagem mecânica dos motores NEMA 17 (Pan/Tilt), câmera e gearbox
* [x] Integração elétrica com CNC Shield V4, drivers DRV8825 em `1/32` passo e relé no pino `A3`
* [x] Calibração de limites angulares (`±135°` X / `-35° a +45°` Y), rampa de aceleração e *auto-sleep*
