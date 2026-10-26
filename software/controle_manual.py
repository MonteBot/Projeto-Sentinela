"""
Script interativo para controle e teste dos motores NEMA 17 via CNC Shield V4 + Arduino Nano
"""
import serial
import serial.tools.list_ports
import time
import threading
import sys

def reader_thread(ser, stop_event):
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                text = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                print(text, end='', flush=True)
            else:
                time.sleep(0.02)
        except Exception:
            break

def main():
    port = "COM8"
    baud = 115200

    print("=" * 60)
    print(f" Conectando ao Arduino Nano em {port} ({baud} baud)...")
    print("=" * 60)

    try:
        ser = serial.Serial(port, baud, timeout=0.1)
    except Exception as e:
        print(f"Erro ao abrir {port}: {e}")
        print("Verifique se o Arduino IDE Serial Monitor ou outro programa nao esta usando a porta.")
        return

    time.sleep(1.0)
    stop_event = threading.Event()
    t = threading.Thread(target=reader_thread, args=(ser, stop_event), daemon=True)
    t.start()

    # Pede o menu de ajuda ao Arduino
    ser.write(b'h\n')

    print("\n[DICA] Comandos rapidos:")
    print("  1 ou x  -> Testar Motor X")
    print("  2 ou y  -> Testar Motor Y")
    print("  4 ou b  -> Testar X e Y juntos")
    print("  t       -> Iniciar movimento continuo")
    print("  s       -> Parar movimento continuo")
    print("  e       -> Ligar / Desligar Drivers (Enable)")
    print("  + / -   -> Ajustar velocidade")
    print("  q       -> Sair\n")

    try:
        while True:
            cmd = input()
            if cmd.strip().lower() == 'q':
                break
            if cmd:
                ser.write((cmd + '\n').encode('utf-8'))
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_event.set()
        time.sleep(0.1)
        ser.close()
        print("\nConexao encerrada.")

if __name__ == '__main__':
    main()
