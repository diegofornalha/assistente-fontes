import os
import json
from datetime import datetime

HEALTHPLAN_LOG = "healthplan_perguntas.json"

def registrar_healthplan(pergunta: str, usuario: str):
    registro = {
        "pergunta": pergunta,
        "usuario": usuario,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if os.path.exists(HEALTHPLAN_LOG):
        with open(HEALTHPLAN_LOG, "r", encoding="utf-8") as f:
            dados = json.load(f)
    else:
        dados = []

    dados.append(registro)

    with open(HEALTHPLAN_LOG, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
