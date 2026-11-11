import os
import time
import threading
import urllib.request
import cv2
import numpy as np
import config
from serial_comm import torreta

PASTA_BLACKLIST = "blacklist"
ARQUIVO_ROSTO_ALVO = os.path.join(PASTA_BLACKLIST, "rosto_alvo.jpg")
ARQUIVO_MODELO_YML = os.path.join(PASTA_BLACKLIST, "modelo_alvo.yml")

os.makedirs(PASTA_BLACKLIST, exist_ok=True)


def localizar_cascade():
    xml = 'haarcascade_frontalface_default.xml'
    caminhos = [
        xml,
        f'/usr/share/opencv4/haarcascades/{xml}',
        f'/usr/local/share/opencv4/haarcascades/{xml}',
        f'/usr/share/opencv/haarcascades/{xml}'
    ]
    if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
        caminhos.insert(0, os.path.join(cv2.data.haarcascades, xml))

    for c in caminhos:
        if os.path.exists(c):
            return c

    url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{xml}"
    try:
        urllib.request.urlretrieve(url, xml)
    except Exception as e:
        print(f"[AVISO] Falha ao baixar XML: {e}")
    return xml


face_cascade = cv2.CascadeClassifier(localizar_cascade())


class GerenciadorBlacklist:
    def __init__(self):
        self.lock = threading.Lock()
        self.alvo_cadastrado = False
        self.rosto_padrao = None
        self.recognizer = None
        self.usar_lbph = False

        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.usar_lbph = True
        except Exception:
            self.usar_lbph = False

        self.carregar_alvo_salvo()

    def _preparar_rosto(self, img_gray):
        rosto = cv2.resize(img_gray, (150, 150))
        return cv2.equalizeHist(rosto)

    def _gerar_variacoes_treino(self, rosto_base):
        amostras = [rosto_base, cv2.flip(rosto_base, 1)]
        for alpha in (0.85, 1.0, 1.15):
            for beta in (-15, 0, 15):
                amostras.append(cv2.convertScaleAbs(rosto_base, alpha=alpha, beta=beta))
        corte = rosto_base[10:140, 10:140]
        amostras.append(cv2.resize(corte, (150, 150)))
        return amostras

    def cadastrar_imagem_bgr(self, img_bgr):
        if img_bgr is None:
            return False, "Imagem invalida."

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))

        if len(faces) > 0:
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces[0]
            recorte_gray = gray[y:y+h, x:x+w]
            recorte_cor = img_bgr[y:y+h, x:x+w]
        else:
            recorte_gray = gray
            recorte_cor = img_bgr

        rosto_prep = self._preparar_rosto(recorte_gray)
        cv2.imwrite(ARQUIVO_ROSTO_ALVO, cv2.resize(recorte_cor, (160, 160)))

        with self.lock:
            self.rosto_padrao = rosto_prep
            if self.usar_lbph and self.recognizer is not None:
                amostras = self._gerar_variacoes_treino(rosto_prep)
                labels = np.array([1] * len(amostras), dtype=np.int32)
                self.recognizer.train(amostras, labels)
                self.recognizer.write(ARQUIVO_MODELO_YML)
            self.alvo_cadastrado = True

        return True, "Alvo cadastrado na Blacklist!"

    def carregar_alvo_salvo(self):
        if not os.path.exists(ARQUIVO_ROSTO_ALVO):
            return
        img = cv2.imread(ARQUIVO_ROSTO_ALVO)
        if img is None:
            return

        if self.usar_lbph and self.recognizer is not None and os.path.exists(ARQUIVO_MODELO_YML):
            try:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                with self.lock:
                    self.rosto_padrao = self._preparar_rosto(gray)
                    self.recognizer.read(ARQUIVO_MODELO_YML)
                    self.alvo_cadastrado = True
                return
            except Exception:
                pass

        self.cadastrar_imagem_bgr(img)

    def verificar_rosto(self, roi_gray):
        with self.lock:
            if not self.alvo_cadastrado or self.rosto_padrao is None:
                return False, 999

            rosto_teste = self._preparar_rosto(roi_gray)

            if self.usar_lbph and self.recognizer is not None:
                id_alvo, confianca = self.recognizer.predict(rosto_teste)
                eh_alvo = (id_alvo == 1 and confianca <= config.LIMITE_CONFIANCA)
                return eh_alvo, int(confianca)
            else:
                res = cv2.matchTemplate(rosto_teste, self.rosto_padrao, cv2.TM_CCOEFF_NORMED)
                similaridade = float(res[0][0])
                dist = int((1.0 - max(0.0, similaridade)) * 150)
                return (dist <= config.LIMITE_CONFIANCA), dist


blacklist_mgr = GerenciadorBlacklist()


class CameraStream:
    def __init__(self):
        self.frame_jpeg = None
        self.ultimo_frame_bgr = None
        self.cond = threading.Condition()
        self.rodando = False
        self.fps_atual = 0.0
        self.seq_frame = 0

    def iniciar(self):
        if not self.rodando:
            self.rodando = True
            threading.Thread(target=self._loop_captura, daemon=True).start()

    def capturar_rosto_atual(self):
        with self.cond:
            if self.ultimo_frame_bgr is None:
                return False, "Sem sinal da camera."
            quadro = self.ultimo_frame_bgr.copy()
        return blacklist_mgr.cadastrar_imagem_bgr(quadro)

    def _abrir_camera(self):
        cap = cv2.VideoCapture(config.CAMERA_ID)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.LARGURA_CAM)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.ALTURA_CAM)
        cap.set(cv2.CAP_PROP_FPS, 30)
        return cap

    def _loop_captura(self):
        cap = self._abrir_camera()

        cx_tela = config.LARGURA_CAM // 2
        cy_tela = config.ALTURA_CAM // 2
        contador_frames = 0
        ultimas_faces = []
        param_jpeg = [int(cv2.IMWRITE_JPEG_QUALITY), config.QUALIDADE_JPEG]

        t_anterior = time.perf_counter()
        fps_ema = 0.0
        falhas = 0

        while self.rodando:
            ret, frame = cap.read()
            t_agora = time.perf_counter()
            dt = t_agora - t_anterior
            t_anterior = t_agora

            if dt > 0.001:
                fps_inst = 1.0 / dt
                fps_ema = fps_inst if fps_ema == 0.0 else (fps_ema * 0.85 + fps_inst * 0.15)
                self.fps_atual = fps_ema
                if contador_frames % 5 == 0:
                    torreta.atualizar_fps(fps_ema)

            if not ret or frame is None:
                falhas += 1
                torreta.atualizar_fps(0.0)
                if falhas >= 6:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    cap = self._abrir_camera()
                    falhas = 0
                frame = np.zeros((config.ALTURA_CAM, config.LARGURA_CAM, 3), dtype=np.uint8)
                cv2.putText(frame, "SEM SINAL DE CAMERA", (55, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                time.sleep(0.2)
            else:
                falhas = 0
                with self.cond:
                    self.ultimo_frame_bgr = frame

                frame_hud = frame.copy()
                est = torreta.obter_estado()
                modo = est["modo"]
                contador_frames += 1

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if not face_cascade.empty() and contador_frames % 2 == 0:
                    ultimas_faces = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.15, minNeighbors=4, minSize=(28, 28)
                    )

                mira_em_rosto_proibido = False
                apenas_rosto_perto = False

                for (fx, fy, fw, fh) in ultimas_faces:
                    margem_x = int(fw * 0.25)
                    limite_pescoco_y = fy + fh + int(fh * config.MARGEM_PROTECAO_PESCOCO)

                    if fh > config.MAX_ALTURA_ROSTO_PX:
                        apenas_rosto_perto = True

                    if (fx - margem_x <= cx_tela <= fx + fw + margem_x) and (fy - 25 <= cy_tela <= limite_pescoco_y):
                        mira_em_rosto_proibido = True

                torreta.definir_trava_rosto(mira_em_rosto_proibido or apenas_rosto_perto)

                if modo in (1, 2):
                    alvo = None
                    pode_atirar = False

                    for (x, y, w, h) in ultimas_faces:
                        cv2.rectangle(frame_hud, (x, y), (x + w, y + h), (0, 215, 255), 1)
                        cv2.putText(frame_hud, "ROSTO [PROTEGIDO]", (x, max(12, y - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 215, 255), 1)

                        if modo == 1:
                            if alvo is None or (w * h) > (alvo[2] * alvo[3]):
                                alvo = (x, y, w, h)
                                pode_atirar = True

                        elif modo == 2:
                            roi_gray = gray[y:y+h, x:x+w]
                            eh_alvo, dist = blacklist_mgr.verificar_rosto(roi_gray)
                            if eh_alvo:
                                if alvo is None or (w * h) > (alvo[2] * alvo[3]):
                                    alvo = (x, y, w, h)
                                    pode_atirar = True
                            else:
                                cv2.putText(frame_hud, f"CIVIL ({dist})", (x, y + h + 13),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)

                    if alvo is not None and pode_atirar:
                        ax, ay, aw, ah = alvo

                        peito_x = ax + (aw // 2)
                        peito_y = ay + int(ah * config.FATOR_DESCIDA_PEITO)

                        larg_peito = int(aw * 1.3)
                        alt_peito = int(ah * 0.9)
                        px1 = max(0, peito_x - larg_peito // 2)
                        py1 = max(0, peito_y - alt_peito // 2)
                        px2 = min(config.LARGURA_CAM - 1, peito_x + larg_peito // 2)
                        py2 = min(config.ALTURA_CAM - 1, peito_y + alt_peito // 2)

                        peito_dentro_da_tela = (peito_y + int(ah * 0.25)) < (config.ALTURA_CAM - 4)
                        peito_visivel = (not apenas_rosto_perto) and peito_dentro_da_tela

                        cor_peito = (0, 0, 255) if peito_visivel else (0, 140, 255)
                        if py1 < config.ALTURA_CAM:
                            cv2.rectangle(frame_hud, (px1, py1), (px2, py2), cor_peito, 2)
                            y_ponto = min(peito_y, config.ALTURA_CAM - 3)
                            cv2.circle(frame_hud, (peito_x, y_ponto), 4, cor_peito, -1)
                            cv2.line(frame_hud, (cx_tela, cy_tela), (peito_x, y_ponto), cor_peito, 1)

                        erro_x = (peito_x - cx_tela) * config.INVERTER_X
                        erro_y = (cy_tela - peito_y) * config.INVERTER_Y

                        if apenas_rosto_perto:
                            torreta.atualizar_automatico(0, 0, 0, "TRAVA: SO ROSTO VISIVEL (MUITO PERTO)")
                        else:
                            vx = int(np.clip(erro_x * config.KP_X, -85, 85)) if abs(erro_x) > config.ZONA_MORTA_PX else 0
                            vy = int(np.clip(erro_y * config.KP_Y, -65, 65)) if abs(erro_y) > config.ZONA_MORTA_PX else 0

                            na_mira_peito = (abs(erro_x) <= config.MARGEM_TIRO_PX and abs(erro_y) <= config.MARGEM_TIRO_PX)

                            if peito_visivel and na_mira_peito and not mira_em_rosto_proibido:
                                gatilho = 1
                                status = "ATIRANDO NO PEITO!"
                            elif not peito_visivel:
                                gatilho = 0
                                status = "TRAVA: PEITO FORA DA TELA (SO ROSTO)"
                            else:
                                gatilho = 0
                                status = "MIRANDO NO PEITO..."

                            torreta.atualizar_automatico(vx, vy, gatilho, status)
                    else:
                        torreta.atualizar_automatico(0, 0, 0, "VIGIANDO...")

                est = torreta.obter_estado()
                if mira_em_rosto_proibido or apenas_rosto_perto:
                    cv2.rectangle(frame_hud, (0, 0), (config.LARGURA_CAM, 22), (0, 0, 180), -1)
                    cv2.putText(frame_hud, "TRAVA ATIVA: PROIBIDO ATIRAR NO ROSTO", (12, 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
                    cor_mira = (0, 140, 255)
                else:
                    cor_mira = (0, 0, 255) if est["gatilho"] else (0, 255, 0)

                cv2.circle(frame_hud, (cx_tela, cy_tela), config.MARGEM_TIRO_PX, cor_mira, 1)
                cv2.line(frame_hud, (cx_tela - 10, cy_tela), (cx_tela + 10, cy_tela), cor_mira, 1)
                cv2.line(frame_hud, (cx_tela, cy_tela - 10), (cx_tela, cy_tela + 10), cor_mira, 1)

                txt_fps = f"FPS: {self.fps_atual:.1f}"
                cv2.putText(frame_hud, txt_fps, (8, config.ALTURA_CAM - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 2)
                cv2.putText(frame_hud, txt_fps, (8, config.ALTURA_CAM - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 128), 1)

                frame = frame_hud

            ok, buffer = cv2.imencode('.jpg', frame, param_jpeg)
            if ok:
                with self.cond:
                    self.frame_jpeg = buffer.tobytes()
                    self.seq_frame += 1
                    self.cond.notify_all()

            time.sleep(0.01)

    def aguardar_frame(self, ultimo_seq):
        with self.cond:
            if self.seq_frame == ultimo_seq:
                self.cond.wait(timeout=0.1)
            return self.frame_jpeg, self.seq_frame


camera_bg = CameraStream()


def gerar_frames():
    camera_bg.iniciar()
    seq = -1
    while True:
        frame_bytes, seq = camera_bg.aguardar_frame(seq)
        if frame_bytes is not None:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
