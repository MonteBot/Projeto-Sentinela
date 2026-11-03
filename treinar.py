import cv2
import numpy as np
import os
from PIL import Image

caminho = 'dataset'
if not os.path.exists(caminho) or len(os.listdir(caminho)) == 0:
    print("ERRO: Nenhuma foto encontrada na pasta 'dataset'.")
    exit()

detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()
amostras_rosto, ids = [], []

for ficheiro in os.listdir(caminho):
    if ficheiro.lower().endswith(('.jpg', '.jpeg', '.png')):
        caminho_imagem = os.path.join(caminho, ficheiro)
        try:
            id_pessoa = int(ficheiro.split(".")[1])
        except:
            continue

        img_pil = Image.open(caminho_imagem).convert('L')
        img_numpy = np.array(img_pil, 'uint8')
        rostos = detector.detectMultiScale(img_numpy)

        for (x, y, w, h) in rostos:
            amostras_rosto.append(img_numpy[y:y+h, x:x+w])
            ids.append(id_pessoa)

if len(amostras_rosto) > 0:
    recognizer.train(amostras_rosto, np.array(ids))
    recognizer.write('blacklist_model.yml')
    print(f"SUCESSO! Modelo criado com {len(amostras_rosto)} rostos.")
else:
    print("ERRO: A IA não encontrou rostos nítidos.")
