import os
import time
import serial
import threading
import config

class ControleTorreta:
    def __init__(self):
        self.arduino = None
        self.porta_conectada = "DESCONECTADO"
        self.lock = threading.Lock()
        self.trava_seguranca_rosto = False
        self.fps_camera = 0.0
        self.ultimo_seq_manual = -1
        self.ultimo_ts_manual = 0.0
        self.pausa_ate_ts = 0.0
        self.estado = {
            "modo": 0,
            "vx": 0,
            "vy": 0,
            "gatilho": 0,
            "status_texto": "MODO MANUAL ATIVO",
            "cmd_especial": None
        }
        self.conectar()

    def conectar(self):
        for p in config.PORTAS_TENTATIVA:
            if os.path.exists(p):
                try:
                    self.arduino = serial.Serial(p, config.BAUD_RATE, timeout=0.02, write_timeout=0.05)
                    time.sleep(2)
                    self.porta_conectada = p
                    print(f"[OK] Arduino Nano conectado em {p}")
                    return
                except Exception as e:
                    print(f"[ERRO] Falha na porta {p}: {e}")
        print("[AVISO] Arduino desconectado. Verifique o cabo USB.")

    def atualizar_fps(self, fps):
        with self.lock:
            self.fps_camera = round(float(fps), 1)

    def definir_trava_rosto(self, bloquear):
        with self.lock:
            self.trava_seguranca_rosto = bool(bloquear)
            if self.trava_seguranca_rosto:
                self.estado["gatilho"] = 0

    def atualizar_manual(self, vx, vy, gatilho, seq=None):
        vx_lim = max(-100, min(100, int(vx)))
        vy_lim = max(-100, min(100, int(vy)))
        with self.lock:
            if seq is not None and seq > 0:
                if seq < self.ultimo_seq_manual and (vx_lim != 0 or vy_lim != 0 or int(gatilho) != 0):
                    return
                self.ultimo_seq_manual = seq
            self.ultimo_ts_manual = time.monotonic()
            self.pausa_ate_ts = 0.0
            g_lim = 0 if self.trava_seguranca_rosto else (1 if int(gatilho) > 0 else 0)
            self.estado["modo"] = 0
            self.estado["vx"] = vx_lim
            self.estado["vy"] = vy_lim
            self.estado["gatilho"] = g_lim
            if self.trava_seguranca_rosto and int(gatilho) > 0:
                self.estado["status_texto"] = "TRAVA ATIVA: PROIBIDO ATIRAR NO ROSTO!"
            else:
                self.estado["status_texto"] = f"MANUAL (X:{vx_lim} Y:{vy_lim} T:{g_lim})"

    def atualizar_automatico(self, vx, vy, gatilho, status):
        with self.lock:
            if self.estado["modo"] in (1, 2):
                g_seguro = 0 if self.trava_seguranca_rosto else (1 if int(gatilho) > 0 else 0)
                self.estado["vx"] = max(-100, min(100, int(vx)))
                self.estado["vy"] = max(-100, min(100, int(vy)))
                self.estado["gatilho"] = g_seguro
                self.estado["status_texto"] = status

    def enviar_especial(self, codigo):
        with self.lock:
            self.estado["modo"] = 0
            self.estado["vx"] = 0
            self.estado["vy"] = 0
            self.estado["gatilho"] = 0
            self.estado["cmd_especial"] = codigo
            self.estado["status_texto"] = f"COMANDO: {codigo}"

    def definir_modo(self, novo_modo):
        nomes = {
            0: "MODO MANUAL ATIVO",
            1: "MODO ASSASSINO (MIRA NO PEITO)",
            2: "MODO BLACKLIST (MIRA NO PEITO)"
        }
        with self.lock:
            self.estado["modo"] = novo_modo if novo_modo in (0, 1, 2) else 0
            self.estado["vx"] = 0
            self.estado["vy"] = 0
            self.estado["gatilho"] = 0
            self.estado["status_texto"] = nomes.get(self.estado["modo"], "MODO MANUAL")
            return self.estado["modo"], self.estado["status_texto"]

    def obter_estado(self):
        with self.lock:
            copia = self.estado.copy()
            copia["trava_rosto"] = self.trava_seguranca_rosto
            copia["porta"] = self.porta_conectada
            copia["fps"] = self.fps_camera
            return copia

    def loop_envio(self):
        while True:
            if self.arduino is None:
                time.sleep(2.0)
                self.conectar()
                continue

            try:
                agora = time.monotonic()
                with self.lock:
                    cmd_esp = self.estado["cmd_especial"]
                    self.estado["cmd_especial"] = None
                    if self.estado["modo"] == 0 and (agora - self.ultimo_ts_manual > 0.35):
                        if self.estado["vx"] != 0 or self.estado["vy"] != 0 or self.estado["gatilho"] != 0:
                            self.estado["vx"] = 0
                            self.estado["vy"] = 0
                            self.estado["gatilho"] = 0
                            self.estado["status_texto"] = "MANUAL (X:0 Y:0 T:0)"
                    vx = self.estado["vx"]
                    vy = self.estado["vy"]
                    g = 0 if self.trava_seguranca_rosto else self.estado["gatilho"]

                if cmd_esp:
                    self.arduino.write(f"{cmd_esp}\n".encode('ascii'))
                    if cmd_esp.upper().startswith('A'):
                        self.pausa_ate_ts = agora + 1.2
                elif agora >= self.pausa_ate_ts:
                    self.arduino.write(f"{vx} {vy} {g}\n".encode('ascii'))
            except Exception as e:
                print(f"[ERRO SERIAL] Reconectando... ({e})")
                try:
                    self.arduino.close()
                except Exception:
                    pass
                self.arduino = None
                self.porta_conectada = "RECONECTANDO..."

            time.sleep(0.04)

    def iniciar_thread(self):
        t = threading.Thread(target=self.loop_envio, daemon=True)
        t.start()

torreta = ControleTorreta()
