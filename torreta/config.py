PORTAS_TENTATIVA = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
BAUD_RATE = 115200

CAMERA_ID = 0
LARGURA_CAM = 320
ALTURA_CAM = 240
QUALIDADE_JPEG = 65

# Limite de confiança para o reconhecimento facial LBPH (menor = mais rigoroso)
LIMITE_CONFIANCA = 85

# Parâmetros da Trava de Segurança (Mira exclusiva no peito / Proibido Rosto)
FATOR_DESCIDA_PEITO = 1.85
MARGEM_PROTECAO_PESCOCO = 0.35
MAX_ALTURA_ROSTO_PX = 90

# Ganhos proporcionais de rastreamento para 320x240
KP_X = 0.40
KP_Y = 0.35
ZONA_MORTA_PX = 10
MARGEM_TIRO_PX = 28

# Mude para -1 caso algum motor gire para o lado oposto ao rastrear
INVERTER_X = 1
INVERTER_Y = 1
