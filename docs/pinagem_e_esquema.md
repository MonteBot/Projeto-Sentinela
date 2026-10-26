# Documentação de Hardware e Pinagem - CNC Shield V4 + Arduino Nano

Este documento detalha o mapeamento de pinos, configurações de jumpers, cuidados elétricos e detalhes sobre os drivers para o **Projeto Sentinela**.

---

## 📌 Tabela de Pinagem (Arduino Nano na CNC Shield V4)

| Função / Sinal | Pino Arduino Nano | Descrição |
| :--- | :--- | :--- |
| **ENABLE (Geral)** | **D8** | Habilita os drivers de passo (Ativo em nível BAIXO / LOW) |
| **Eixo X - STEP (Modo Padrão)** | **D2** | Pulsos de passo para o Motor X |
| **Eixo X - DIR (Modo Padrão)** | **D5** | Direção de giro do Motor X |
| **Eixo Y - STEP (Modo Padrão)** | **D3** | Pulsos de passo para o Motor Y |
| **Eixo Y - DIR (Modo Padrão)** | **D6** | Direção de giro do Motor Y |
| **Eixo Z - STEP** | **D4** | Reservado para o Eixo Z |
| **Eixo Z - DIR** | **D7** | Reservado para o Eixo Z |

> ⚠️ **Nota sobre Clones da CNC Shield V4:**
> Algumas placas possuem as trilhas invertidas de fábrica (D5=STEP/D2=DIR e D6=STEP/D3=DIR). O firmware do projeto inclui suporte dinâmico a ambos os modos através do comando `'m'` ou botão na interface gráfica.

---

## ⚡ Requisitos Elétricos

1. **Alimentação da Lógica (5V):**
   - Fornecida pelo cabo USB conectado ao Arduino Nano.
2. **Alimentação dos Motores (12V - 24V):**
   - Deve ser conectada diretamente no **borne azul** de parafusos da CNC Shield V4.
   - Fonte recomendada: **12V DC com corrente mínima de 3A a 5A**.
   - **Nunca** opere motores de passo apenas com a energia USB.

---

## 🛠️ Drivers Suportados: DRV8825 e A4988

### Orientação dos Drivers
- Ao encaixar os drivers nos soquetes, confirme o alinhamento do pino **`EN`** (Enable) do driver com a inscrição **`EN`** na placa CNC Shield.
- No **DRV8825**, o potenciômetro de ajuste de corrente (trimpot metálico) fica voltado para o lado do pino `EN`/`VMOT` (oposto ao A4988).

### Microstepping (Jumpers sob o driver)
- Sem jumpers instalados: **Full Step (Passo Completo - 200 passos/volta)**.
- Com jumpers instalados no DRV8825: pode atingir até **1/32 de passo** (6400 passos/volta).
- O firmware e os softwares de controle já são calibrados com delays e passos adaptáveis para qualquer resolução configurada.
