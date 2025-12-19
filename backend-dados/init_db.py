import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # /assistente-fontes
conn = sqlite3.connect(str(BASE_DIR / "logs.db"))
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    pergunta TEXT,
    resposta TEXT,
    tipo_prompt TEXT,
    contexto TEXT,
    modulo TEXT,
    aula TEXT,
    data TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("✅ Tabela 'logs' criada ou ajustada com sucesso.")
