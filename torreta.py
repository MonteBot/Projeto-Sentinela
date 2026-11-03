import cv2
import time
import threading
import evdev
import sys
from flask import Flask, render_template, Response, jsonify
from gpiozero import AngularServo, OutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory

# HARDWARE E PINOS
factory = PiGPIOFactory()
PIN_SERVO_PAN = 17  
PIN_SERVO_TILT = 27 
PIN_RELE_GATILHO = 22

servo_pan = AngularServo(PIN_SERVO_PAN, min_angle=-90, max_angle=90, pin_factory=factory)
servo_tilt = AngularServo(PIN_SERVO_TILT, min_angle=-90, max_angle=90, pin_factory=factory)
gatilho = OutputDevice(PIN_RELE_GATILHO, active_high=True, initial_value=False)

# ESTADO GLOBAL E TELEMETRIA
estado = {
    'modo': 'MANUAL',
    'frame_atual': None,
    'rajada_em_curso': False,
    'fps': 0.0,
    'travado_seguranca': False,
    'motivo_trava': 'Sistema em Standby',
    'status_disparo': 'Em espera'
}
lock = threading.Lock()

RES_W, RES_H = 320, 240
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RES_H)

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

try:
    recognizer.read('blacklist_model.yml')
except:
    print("[ERRO] blacklist_model.yml não encontrado. Executa o treinar.py primeiro.")
    sys.exit()

def disparar_rajada():
    with lock:
        if estado['rajada_em_curso']: return
        estado['rajada_em_curso'] = True
    def rotina_tiro():
        for _ in range(3):
            gatilho.on()
            time.sleep(0.1)
            gatilho.off()
            time.sleep(0.15)
        with lock: estado['rajada_em_curso'] = False
    threading.Thread(target=rotina_tiro, daemon=True).start()

def mapear_angulo(coordenada, limite):
    return -90 + ((coordenada / limite) * 180)

def loop_camera():
    frame_count = 0
    tempo_inicial = time.time()
    fps_atual = 0.0

    while True:
        ret, frame = cap.read()
        if not ret: continue
        
        # Cálculo de FPS real
        frame_count += 1
        tempo_atual = time.time()
        if tempo_atual - tempo_inicial >= 1.0:
            fps_atual = frame_count / (tempo_atual - tempo_inicial)
            frame_count = 0
            tempo_inicial = tempo_atual

        with lock: 
            modo_atual = estado['modo']
            estado['fps'] = fps_atual
        
        if modo_atual == 'MANUAL':
            cv2.putText(frame, "MANUAL", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            with lock:
                estado['travado_seguranca'] = False
                estado['motivo_trava'] = 'Modo Manual (Standby)'
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostos = face_cascade.detectMultiScale(gray, 1.3, 4, minSize=(30, 30))
            alvo_valido = False
            
            for (x, y, w, h) in rostos:
                centro_x = x + (w // 2)
                # Cálculo do peito (deslocado para baixo)
                peito_y = y + (h // 2) + int(h * 1.5)
                id_alvo, confianca = recognizer.predict(gray[y:y+h, x:x+w])
                
                if confianca < 80:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    
                    # REGRA DE SEGURANÇA: Fail-safe se o peito sair da tela vertical
                    if peito_y >= RES_H - 10:
                        cv2.putText(frame, "TRAVADO: PEITO FORA", (10, RES_H-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                        with lock:
                            estado['travado_seguranca'] = True
                            estado['motivo_trava'] = "TRAVADO: Peito fora da tela"
                    else:
                        alvo_valido = True
                        cv2.circle(frame, (centro_x, peito_y), 5, (0, 0, 255), -1)
                        with lock:
                            estado['travado_seguranca'] = False
                            estado['motivo_trava'] = "Alvo enquadrado no peito"
                        try:
                            servo_pan.angle = -mapear_angulo(centro_x, RES_W)
                            servo_tilt.angle = -mapear_angulo(peito_y, RES_H)
                        except ValueError: pass
                        disparar_rajada()
                        break
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 1)
            
            if not alvo_valido and not estado['rajada_em_curso']:
                gatilho.off()
                with lock:
                    estado['travado_seguranca'] = False
                    estado['motivo_trava'] = "Nenhum alvo na blacklist"

        with lock: estado['frame_atual'] = frame.copy()
        time.sleep(0.02)

def loop_gamepad():
    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    gamepad = next((d for d in devices if 'pad' in d.name.lower() or 'xbox' in d.name.lower()), None)
    if not gamepad: return
    for event in gamepad.read_loop():
        with lock:
            if estado['modo'] == 'AUTO': continue
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_X:
                try: servo_pan.angle = -(((event.value / 32767.5) - 1) * 90)
                except ValueError: pass
            elif event.code == evdev.ecodes.ABS_Y:
                try: servo_tilt.angle = (((event.value / 32767.5) - 1) * 90)
                except ValueError: pass
        elif event.type == evdev.ecodes.EV_KEY:
            if event.code == 315 or event.code == evdev.ecodes.BTN_TR:
                if event.value == 1: gatilho.on()
                elif event.value == 0: gatilho.off()

app = Flask(__name__)

def stream():
    while True:
        with lock: frame = estado['frame_atual']
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/video_feed')
def video_feed(): return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetria')
def telemetria():
    with lock:
        return jsonify({
            "fps": round(estado.get('fps', 0), 1),
            "travado": estado.get('travado_seguranca', False),
            "mensagem_trava": estado.get('motivo_trava', 'Normal'),
            "disparando": estado.get('rajada_em_query', False) or estado.get('rajada_em_curso', False),
            "mensagem_disparo": "FOGO! Rajada em curso" if estado.get('rajada_em_curso') else "Em espera / Seguro"
        })

@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    with lock:
        estado['modo'] = 'AUTO' if estado['modo'] == 'MANUAL' else 'MANUAL'
        gatilho.off() 
        return jsonify({"modo": estado['modo']})

if __name__ == '__main__':
    threading.Thread(target=loop_camera, daemon=True).start()
    threading.Thread(target=loop_gamepad, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
