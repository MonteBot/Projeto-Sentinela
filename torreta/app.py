import os
import time
import signal
import subprocess
import logging


def liberar_instancia_anterior():
    meu_pid = os.getpid()
    try:
        out = subprocess.check_output(['pgrep', '-f', 'app.py'], text=True)
        pids = [
            int(p) for p in out.strip().splitlines()
            if p.strip().isdigit() and int(p) != meu_pid
        ]
        if pids:
            print(f"[SISTEMA] Liberando camera e porta 5000 da instancia anterior (PID {pids})...")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
            time.sleep(0.8)
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            time.sleep(0.4)
    except Exception:
        pass


liberar_instancia_anterior()

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, render_template, send_file
import config
from serial_comm import torreta
from visao import gerar_frames, blacklist_mgr, camera_bg, ARQUIVO_ROSTO_ALVO

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/')
def index():
    return render_template(
        'index.html',
        porta=torreta.porta_conectada,
        tem_alvo=blacklist_mgr.alvo_cadastrado,
        limite=config.LIMITE_CONFIANCA
    )


@app.route('/stream')
def stream():
    resp = Response(gerar_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route('/cmd')
def receber_cmd():
    vx = request.args.get('vx', default=0, type=int)
    vy = request.args.get('vy', default=0, type=int)
    g = request.args.get('g', default=0, type=int)
    seq = request.args.get('seq', default=None, type=int)
    cid = request.args.get('cid', default=None, type=str)
    torreta.atualizar_manual(vx, vy, g, seq, cid)
    return "OK", 200


@app.route('/especial')
def receber_especial():
    c = request.args.get('c', '')
    if c:
        torreta.enviar_especial(c)
    return "OK", 200


@app.route('/set_modo/<int:m>')
def alterar_modo(m):
    modo, status = torreta.definir_modo(m)
    return jsonify({"modo": modo, "status": status})


@app.route('/status')
def obter_status():
    return jsonify(torreta.obter_estado())


@app.route('/upload_blacklist', methods=['POST'])
def upload_blacklist():
    if 'foto' not in request.files:
        return jsonify({"ok": False, "msg": "Nenhum arquivo enviado."}), 400
    arq = request.files['foto']
    dados = np.frombuffer(arq.read(), np.uint8)
    img = cv2.imdecode(dados, cv2.IMREAD_COLOR)
    ok, msg = blacklist_mgr.cadastrar_imagem_bgr(img)
    return jsonify({"ok": ok, "msg": msg})


@app.route('/capturar_blacklist', methods=['POST'])
def capturar_blacklist():
    ok, msg = camera_bg.capturar_rosto_atual()
    return jsonify({"ok": ok, "msg": msg})


@app.route('/set_sensibilidade/<int:val>')
def set_sensibilidade(val):
    config.LIMITE_CONFIANCA = max(40, min(140, val))
    return jsonify({"ok": True, "limite": config.LIMITE_CONFIANCA})


@app.route('/foto_alvo')
def foto_alvo():
    if os.path.exists(ARQUIVO_ROSTO_ALVO):
        resp = send_file(ARQUIVO_ROSTO_ALVO, mimetype='image/jpeg')
        resp.headers['Cache-Control'] = 'no-store, max-age=0'
        return resp
    return "", 404


if __name__ == '__main__':
    camera_bg.iniciar()
    torreta.iniciar_thread()
    print(f"[MONTEBOT] Painel ativo em http://0.0.0.0:5000 (Serial: {torreta.porta_conectada})")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
