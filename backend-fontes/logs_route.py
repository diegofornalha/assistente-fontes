# logs_route.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import sqlite3
import csv
import io
from pathlib import Path

from auth_utils import get_current_user

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent  # /assistente-fontes
LOGS_DB_PATH = str(BASE_DIR / "logs.db")

def _ensure_logs_table(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
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
        """
    )
    conn.commit()

@router.get("/logs")
def exportar_logs_csv(user: str = Depends(get_current_user)):
    """
    Retorna um CSV com todas as entradas da tabela 'logs' do seu banco SQLite.
    A rota é /logs e só pode ser acessada por usuários autenticados.
    """
    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM logs ORDER BY id DESC")
    registros = cursor.fetchall()
    colunas = [desc[0] for desc in cursor.description]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(colunas)
    writer.writerows(registros)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logs.csv"}
    )
