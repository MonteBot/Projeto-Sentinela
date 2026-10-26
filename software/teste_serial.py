import serial
import time
import sys

def main():
    port = 'COM8'
    baud = 115200

    print(f"Conectando a {port} a {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
    except Exception as e:
        print(f"Erro ao abrir porta {port}: {e}")
        return

    # Reinicia o Arduino via DTR para capturar a inicializacao
    ser.dtr = False
    time.sleep(0.1)
    ser.dtr = True
    time.sleep(0.5)

    print("\n--- Mensagens do Arduino Nano (Inicializacao e Auto-Check) ---")
    start_time = time.time()
    while time.time() - start_time < 5.0:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').rstrip()
            if line:
                print(f"[ARDUINO] {line}")

    # Envia comando para testar motor X
    print("\n--- Enviando comando '1' (Testar Motor X) ---")
    ser.write(b'1\n')
    start_time = time.time()
    while time.time() - start_time < 3.0:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').rstrip()
            if line:
                print(f"[ARDUINO] {line}")

    # Envia comando para testar motor Y
    print("\n--- Enviando comando '2' (Testar Motor Y) ---")
    ser.write(b'2\n')
    start_time = time.time()
    while time.time() - start_time < 3.0:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').rstrip()
            if line:
                print(f"[ARDUINO] {line}")

    # Envia comando para testar ambos
    print("\n--- Enviando comando '4' (Testar X e Y Juntos) ---")
    ser.write(b'4\n')
    start_time = time.time()
    while time.time() - start_time < 3.0:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').rstrip()
            if line:
                print(f"[ARDUINO] {line}")

    ser.close()
    print("\n--- Teste via Serial finalizado com sucesso! ---")

if __name__ == '__main__':
    main()
