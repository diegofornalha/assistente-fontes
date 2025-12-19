import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # /assistente-fontes
DB_PATH = str(BASE_DIR / "logs.db")

def registrar_log(usuario, pergunta, resposta, contexto, tipo_prompt, modulo=None, aula=None, data=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            pergunta TEXT,
            resposta TEXT,
            contexto TEXT,
            tipo_prompt TEXT,
            modulo TEXT,
            aula TEXT,
            data TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if data is None:
        data = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO logs (usuario, pergunta, resposta, contexto, tipo_prompt, modulo, aula, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (usuario, pergunta, resposta, contexto, tipo_prompt, modulo, aula, data))

    conn.commit()
    conn.close()
