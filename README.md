# 🛡️ Projeto Sentinela

Controle automatizado e manual de torreta pan-tilt com 2 eixos utilizando **Arduino Nano**, **CNC Shield V4**, drivers **DRV8825** e motores de passo **NEMA 17**.

---

## 📁 Estrutura do Repositório

```
Projeto-Sentinela/
├── README.md                     # Documentação principal do projeto
├── requirements.txt              # Dependências Python (pyserial)
├── .gitignore                    # Arquivos ignorados pelo Git
├── docs/
│   └── pinagem_e_esquema.md      # Pinagem detalhada, cuidados elétricos e jumpers
├── firmware/
│   └── Torreta/
│       └── Torreta.ino           # Firmware Arduino (controle serial, giro contínuo e jog)
└── software/
    ├── painel_controle.py        # Interface Gráfica (GUI) em Tkinter com suporte a teclado
    ├── controle_manual.py        # Terminal interativo CLI
    └── teste_serial.py           # Script de diagnóstico e validação serial
```

---

## ⚙️ Componentes de Hardware

- **1x Arduino Nano** (ATmega328P)
- **1x Placa de Expansão CNC Shield V4** (3 Eixos para Nano, 12V-36V)
- **2x Drivers de Passo DRV8825** (ou A4988)
- **2x Motores de Passo NEMA 17** (1.8° por passo)
- **1x Fonte de Alimentação Externa 12V** (3A a 5A)

---

## ⚡ Cuidados Críticos de Instalação

1. **Alimentação dos Motores:** Os motores exigem alimentação de **12V DC** ligada no borne de parafusos azul da CNC Shield V4. Apenas o cabo USB não fornece tensão e corrente suficientes para movimentar as bobinas.
2. **Posição dos Drivers:** Certifique-se de alinhar o pino **`EN`** do driver DRV8825 com o pino **`EN`** na CNC Shield. Encaixar o módulo invertido causa queima imediata.
3. **Inversão de Trilhas em Clones V4:** Muitas versões da Shield V4 possuem os pinos de Step e Dir invertidos. O firmware deste projeto possui compatibilidade nativa com ambas as versões (alterne pelo comando `'m'` ou na interface gráfica).

---

## 🚀 Como Usar

### 1. Gravação do Firmware no Arduino Nano

Abra a pasta `firmware/Torreta/` na Arduino IDE:
1. Conecte o cabo USB no notebook.
2. Selecione a placa: **Arduino Nano**.
3. Selecione o processador: **ATmega328P**.
4. Selecione a porta serial (ex: `COM8`).
5. Clique em **Upload**.

*(Também pode ser compilado e gravado via `arduino-cli`:)*
```bash
arduino-cli compile --fqbn arduino:avr:nano firmware/Torreta
arduino-cli upload -p COM8 --fqbn arduino:avr:nano firmware/Torreta
```

---

### 2. Controle via Interface Gráfica (GUI)

Instale as dependências:
```bash
pip install -r requirements.txt
```

Inicie o painel de controle com suporte a botões visuais e teclado:
```bash
python software/painel_controle.py
```

#### Controles Disponíveis:
- **`W` / Seta Cima:** Move Eixo Y para Cima
- **`S` / Seta Baixo:** Move Eixo Y para Baixo
- **`A` / Seta Esquerda:** Move Eixo X para a Esquerda
- **`D` / Seta Direita:** Move Eixo X para a Direita
- **Espaço:** Alterna Giro Contínuo
- **Botão Alternar Pinos (`M`):** Alterna mapeamento padrão (`D2/D3`) ou invertido clone (`D5/D6`)
- **`E`:** Desabilita/Habilita as bobinas dos motores (livres/travados)

---

### 3. Controle via Monitor Serial (Sem Interface Gráfica)

Abra o Monitor Serial da Arduino IDE na porta correspondente a **`115200 baud`**:
- `w` / `s` / `a` / `d`: Movimenta eixos
- `c`: Ativa/Desativa giro contínuo
- `m`: Alterna pinagem da placa
- `+` / `-`: Ajusta velocidade
- `e`: Solta/Trava motores
- `h`: Exibe ajuda
