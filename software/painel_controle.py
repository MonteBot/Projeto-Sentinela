"""
PAINEL DE CONTROLE GRAFICO - TORRETA CNC SHIELD V4 + DRV8825
Interface visual interativa para controlar os eixos X e Y.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import threading
import time

PORT = "COM8"
BAUD = 115200

class TorretaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle da Torreta - CNC Shield V4")
        self.root.geometry("540x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.ser = None
        self.connected = False
        self.stop_thread = threading.Event()

        self.setup_ui()
        self.connect_serial()

        # Teclas de atalho no teclado
        self.root.bind("<Up>", lambda e: self.send_cmd('w'))
        self.root.bind("<Down>", lambda e: self.send_cmd('s'))
        self.root.bind("<Left>", lambda e: self.send_cmd('a'))
        self.root.bind("<Right>", lambda e: self.send_cmd('d'))
        self.root.bind("<w>", lambda e: self.send_cmd('w'))
        self.root.bind("<s>", lambda e: self.send_cmd('s'))
        self.root.bind("<a>", lambda e: self.send_cmd('a'))
        self.root.bind("<d>", lambda e: self.send_cmd('d'))
        self.root.bind("<space>", lambda e: self.send_cmd('c'))

    def setup_ui(self):
        # Titulo
        title = tk.Label(self.root, text="🎮 CONTROLE DA TORRETA", font=("Arial", 16, "bold"), fg="#cdd6f4", bg="#1e1e2e")
        title.pack(pady=10)

        # Status Conexao
        self.status_lbl = tk.Label(self.root, text="Conectando à COM8...", font=("Arial", 10), fg="#f9e2af", bg="#1e1e2e")
        self.status_lbl.pack(pady=2)

        # Frame dos Botoes de Direcao (D-Pad)
        pad_frame = tk.Frame(self.root, bg="#1e1e2e")
        pad_frame.pack(pady=15)

        btn_style = {"font": ("Arial", 12, "bold"), "width": 8, "height": 2, "bg": "#313244", "fg": "#cdd6f4", "activebackground": "#585b70", "activeforeground": "#ffffff"}

        # Cima (Y+)
        self.btn_up = tk.Button(pad_frame, text="▲ CIMA\n(Y+ / W)", command=lambda: self.send_cmd('w'), **btn_style)
        self.btn_up.grid(row=0, column=1, padx=5, pady=5)

        # Esquerda (X-)
        self.btn_left = tk.Button(pad_frame, text="◀ ESQ\n(X- / A)", command=lambda: self.send_cmd('a'), **btn_style)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)

        # Centro (Giro Continuo)
        self.btn_cont = tk.Button(pad_frame, text="🔄 GIRO\nCONT.", command=lambda: self.send_cmd('c'), font=("Arial", 10, "bold"), width=8, height=2, bg="#89b4fa", fg="#11111b")
        self.btn_cont.grid(row=1, column=1, padx=5, pady=5)

        # Direita (X+)
        self.btn_right = tk.Button(pad_frame, text="DIR ▶\n(X+ / D)", command=lambda: self.send_cmd('d'), **btn_style)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)

        # Baixo (Y-)
        self.btn_down = tk.Button(pad_frame, text="▼ BAIXO\n(Y- / S)", command=lambda: self.send_cmd('s'), **btn_style)
        self.btn_down.grid(row=2, column=1, padx=5, pady=5)

        # Botoes de Funcoes Especiais
        func_frame = tk.Frame(self.root, bg="#1e1e2e")
        func_frame.pack(pady=10)

        self.btn_map = tk.Button(func_frame, text="🔀 Alternar Pinos (D2/D3 ⇄ D5/D6)", font=("Arial", 10, "bold"), bg="#a6e3a1", fg="#11111b", command=lambda: self.send_cmd('m'), width=32, height=1)
        self.btn_map.grid(row=0, column=0, columnspan=2, pady=4)

        self.btn_en = tk.Button(func_frame, text="⚡ Soltar / Travar Motores (E)", font=("Arial", 10), bg="#fab387", fg="#11111b", command=lambda: self.send_cmd('e'), width=32, height=1)
        self.btn_en.grid(row=1, column=0, columnspan=2, pady=4)

        # Ajuste de Velocidade
        spd_frame = tk.Frame(self.root, bg="#1e1e2e")
        spd_frame.pack(pady=5)
        tk.Button(spd_frame, text="➖ Mais Lento (-)", command=lambda: self.send_cmd('-'), bg="#45475a", fg="#cdd6f4", width=14).pack(side=tk.LEFT, padx=5)
        tk.Button(spd_frame, text="➕ Mais Rápido (+)", command=lambda: self.send_cmd('+'), bg="#45475a", fg="#cdd6f4", width=14).pack(side=tk.LEFT, padx=5)

        # Caixa de Log Serial
        log_label = tk.Label(self.root, text="Respostas do Arduino:", font=("Arial", 9, "bold"), fg="#a6adc8", bg="#1e1e2e")
        log_label.pack(anchor="w", padx=25, pady=(10, 2))

        self.log_txt = tk.Text(self.root, height=7, width=62, font=("Consolas", 9), bg="#11111b", fg="#a6e3a1", insertbackground="white")
        self.log_txt.pack(padx=20, pady=(0, 10))

    def connect_serial(self):
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.1)
            self.connected = True
            self.status_lbl.config(text=f"Conectado com sucesso em {PORT} ({BAUD} baud)", fg="#a6e3a1")
            
            # Inicia thread de leitura
            t = threading.Thread(target=self.serial_reader, daemon=True)
            t.start()

            # Envia comando de ajuda para sincronizar
            time.sleep(0.5)
            self.ser.write(b'h\n')
        except Exception as e:
            self.connected = False
            self.status_lbl.config(text=f"Erro ao conectar na {PORT}: {e}", fg="#f38ba8")

    def serial_reader(self):
        while not self.stop_thread.is_set():
            if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                try:
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                    self.log_txt.insert(tk.END, data)
                    self.log_txt.see(tk.END)
                except Exception:
                    break
            time.sleep(0.02)

    def send_cmd(self, char):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(char.encode('utf-8'))
            except Exception as e:
                self.log_txt.insert(tk.END, f"\nErro ao enviar: {e}\n")
        else:
            self.log_txt.insert(tk.END, "\n[AVISO] Porta Serial não conectada.\n")

    def on_close(self):
        self.stop_thread.set()
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = TorretaApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
