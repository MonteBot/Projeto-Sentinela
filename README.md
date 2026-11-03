# Projeto Sentinela

Sistema de torreta automatizada. O projeto une visão computacional e eletrônica para detectar e rastrear rostos em tempo real.

## 🏗️ Como Funciona (Arquitetura)
Para que o sistema funcione, o processamento pesado foi separado do controle físico:
- **Raspberry Pi (O Cérebro):** Roda o script Python (`torreta.py`) com OpenCV. Ele lê a imagem da câmera, encontra o rosto e calcula o centro. Depois, envia essas coordenadas via cabo USB (Serial) para o Arduino. Também hospeda a interface Web (`index.html`).
- **Arduino (O Músculo):** Recebe as coordenadas pela porta Serial e move os dois servomotores (Eixos X e Y - Pan/Tilt) para manter a câmera apontada para o alvo.

## ⚙️ Hardware Necessário
- Raspberry Pi
- Arduino Uno/Nano
- 2x Servomotores (Pan e Tilt)
- Módulo de Câmera ou Webcam USB
- Fonte de alimentação externa (para não puxar a corrente dos servos direto do Raspberry Pi)

## 🚀 Instalação e Execução

1. **Instalar dependências no Raspberry Pi:**
   ```bash
   pip install -r requirements.txt

```

2. **Configurar o Arduino:**
Abra o arquivo `arduino/sentinela_cnc.ino` no Arduino IDE e faça o upload para a placa.
3. **Iniciar o sistema:**
No terminal do Raspberry Pi, execute:
```bash
python torreta.py

```


4. **Acesso Web:**
Abra o navegador em qualquer PC na mesma rede e acesse: `http://<IP_DO_RASPBERRY>:5000`.

## 📅 Cronograma e Status do Projeto

### Fase 1: Software e Repositório (Concluído)

* [x] Script de visão computacional (`torreta.py`)
* [x] Integração serial e código de controle (`sentinela_cnc.ino`)
* [x] Interface Web para controle manual e feed de vídeo (`index.html`)
* [x] Criar repositório e estruturar pastas no GitHub
* [x] Documentação base (README) para a equipe

### Fase 2: Hardware e Testes Físicos (Pendentes)

* [ ] **Montagem mecânica:** Fixar a câmera e os servomotores no suporte da torreta.
* [ ] **Alimentação elétrica:** Ligar a fonte de energia separada para os servomotores (com GND unificado com o Arduino).
* [ ] **Calibração:** Ajustar os limites de ângulo máximo/mínimo e a velocidade de resposta (PID) dos motores.
* [ ] **Automação:** Configurar o Raspberry Pi (via Systemd) para iniciar o script de rastreamento automaticamente ao ligar na tomada.
