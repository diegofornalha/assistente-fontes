import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path
from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from jose import jwt

from search_engine import retrieve_relevant_context
from gpt_utils import generate_answer, generate_answer_stream
from db_logs import registrar_log
from logs_route import router as logs_router
from prompt_router import inferir_tipo_de_prompt
from healthplan_log import registrar_healthplan

import re

app = FastAPI()

# Caminhos absolutos (não dependem do diretório atual ao rodar o uvicorn)
BASE_DIR = Path(__file__).resolve().parent.parent  # /assistente-fontes
CHAT_DIR = BASE_DIR / "chat-simples"
LOGS_DB_PATH = str(BASE_DIR / "logs.db")
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
CLAUDE_SESSION_PREFIX = "claude:"

# Garante que as rotas de histórico funcionem mesmo no primeiro start (sem init_db.py)
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

def _ensure_session_meta_table(conn: sqlite3.Connection) -> None:
    """
    Metadados de sessões (ex.: ocultar sessão do histórico sem deletar arquivo).
    Usamos session_id como chave (inclui 'claude:<uuid>').
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS session_meta (
            session_id TEXT PRIMARY KEY,
            hidden INTEGER DEFAULT 0,
            title TEXT,
            summary TEXT,
            tags TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Verificar se a coluna summary já existe (para migrations)
    cursor.execute("PRAGMA table_info(session_meta)")
    columns = [col[1] for col in cursor.fetchall()]

    # Adicionar colunas que podem não existir
    if 'title' not in columns:
        cursor.execute("ALTER TABLE session_meta ADD COLUMN title TEXT")
    if 'summary' not in columns:
        cursor.execute("ALTER TABLE session_meta ADD COLUMN summary TEXT")
    if 'tags' not in columns:
        cursor.execute("ALTER TABLE session_meta ADD COLUMN tags TEXT")

    conn.commit()

def _get_hidden_session_ids(conn: sqlite3.Connection) -> set[str]:
    _ensure_session_meta_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM session_meta WHERE hidden = 1")
    rows = cursor.fetchall()
    hidden: set[str] = set()
    for (sid,) in rows:
        if isinstance(sid, str) and sid:
            hidden.add(sid)
    return hidden

def _set_session_hidden(conn: sqlite3.Connection, session_id: str, hidden: bool) -> None:
    _ensure_session_meta_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_meta(session_id, hidden, updated_at)
        VALUES(?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET hidden=excluded.hidden, updated_at=CURRENT_TIMESTAMP
        """,
        (session_id, 1 if hidden else 0),
    )
    conn.commit()

def _save_session_metadata(conn: sqlite3.Connection, session_id: str, title: Optional[str] = None,
                           summary: Optional[str] = None, tags: Optional[str] = None) -> None:
    """
    Salva metadados da sessão (título, resumo, tags).
    """
    _ensure_session_meta_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_meta(session_id, title, summary, tags, updated_at)
        VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            title=COALESCE(excluded.title, session_meta.title),
            summary=COALESCE(excluded.summary, session_meta.summary),
            tags=COALESCE(excluded.tags, session_meta.tags),
            updated_at=CURRENT_TIMESTAMP
        """,
        (session_id, title, summary, tags),
    )
    conn.commit()

def _get_session_metadata(conn: sqlite3.Connection, session_id: str) -> dict:
    """
    Recupera metadados da sessão.
    """
    _ensure_session_meta_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id, hidden, title, summary, tags, updated_at FROM session_meta WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    if row:
        return {
            'session_id': row[0],
            'hidden': bool(row[1]),
            'title': row[2],
            'summary': row[3],
            'tags': row[4],
            'updated_at': row[5]
        }
    return {}

def _safe_iso_from_mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return datetime.utcnow().isoformat()

def _count_jsonl_lines(path: Path, max_lines: int = 50000) -> int:
    """Conta linhas (aprox) sem carregar tudo em memória."""
    try:
        n = 0
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                n += 1
                if n >= max_lines:
                    break
        return n
    except Exception:
        return 0

def _infer_claude_label_from_jsonl(path: Path) -> Optional[str]:
    """
    Heurística: muitos usuários colocam o nome na primeira mensagem do Claude Code
    (ex.: "Ana Luiza Claude Code", "Felipe Claude Code").
    Retorna um label curto e limpo se conseguir inferir.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in range(10):  # só as primeiras linhas
                raw = f.readline()
                if not raw:
                    break
                line = raw.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if item.get("type") != "user":
                    continue
                msg = item.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    text = content.strip()
                    # remove "Claude Code" do fim (case-insensitive)
                    text = re.sub(r"\s*claude\s*code\s*$", "", text, flags=re.IGNORECASE).strip()
                    # remove "Claude" do fim, se sobrar
                    text = re.sub(r"\s*claude\s*$", "", text, flags=re.IGNORECASE).strip()
                    # não devolve label vazio ou genérico demais
                    if text and len(text) <= 40 and text.lower() not in ("oi", "olá", "ola", "teste", "test"):
                        return text
                    return None
    except Exception:
        return None
    return None

def _should_include_claude_jsonl(path: Path) -> bool:
    """
    Filtra arquivos "técnicos" criados pelo Claude Code, como sidechains/agents e warmups.
    Queremos listar no histórico apenas conversas "de fato".
    """
    # Ignore arquivos de agent-sidechain pelo nome (comum no claude -r)
    try:
        if path.name.startswith("agent-"):
            return False
    except Exception:
        pass

    try:
        has_user_message = False
        has_assistant_message = False
        summary_only = True
        
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in range(50):  # Aumenta para 50 linhas para verificar melhor
                raw = f.readline()
                if not raw:
                    break
                line = raw.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue

                item_type = item.get("type")
                
                # Se encontrou mensagem de usuário ou assistente, não é só summary
                if item_type == "user":
                    has_user_message = True
                    summary_only = False
                elif item_type == "assistant":
                    has_assistant_message = True
                    summary_only = False
                elif item_type == "summary":
                    # Summary sozinho não conta como conteúdo real
                    continue

                # Sidechain/agent do Claude Code
                if item.get("isSidechain") is True or item.get("agentId"):
                    return False

                msg = item.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                    # Warmup é tipicamente um arquivo técnico de inicialização
                    if isinstance(content, str) and content.strip().lower() == "warmup":
                        return False

        # Se o arquivo só tem summary e não tem mensagens reais, filtra
        if summary_only:
            return False
            
        # Se tem pelo menos uma mensagem de usuário ou assistente, inclui
        return has_user_message or has_assistant_message
    except Exception:
        # Em caso de erro de leitura, não polui a lista
        return False

def _iter_claude_project_jsonl_files() -> list[Path]:
    """Lista sessões do Claude Code salvas em ~/.claude/projects/<projeto>/*.jsonl"""
    files: list[Path] = []
    try:
        if not CLAUDE_PROJECTS_DIR.exists():
            return files
        for project_dir in sorted(CLAUDE_PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl_file in sorted(project_dir.glob("*.jsonl")):
                if jsonl_file.is_file():
                    files.append(jsonl_file)
    except Exception:
        return files
    return files

def _find_claude_session_file(session_uuid: str) -> Optional[Path]:
    """Resolve 'uuid' -> ~/.claude/projects/*/<uuid>.jsonl (se existir)."""
    if not session_uuid:
        return None
    try:
        if not CLAUDE_PROJECTS_DIR.exists():
            return None
        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{session_uuid}.jsonl"
            if candidate.exists() and candidate.is_file():
                return candidate
    except Exception:
        return None
    return None

def _is_safe_claude_session_path(path: Path) -> bool:
    """Garante que só apagamos arquivos dentro de ~/.claude/projects e com sufixo .jsonl."""
    try:
        resolved = path.resolve()
        base = CLAUDE_PROJECTS_DIR.resolve()
        if resolved.suffix.lower() != ".jsonl":
            return False
        return base in resolved.parents
    except Exception:
        return False

def _load_claude_session_entries(session_uuid: str) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Lê o JSONL do Claude Code e devolve (entries, model).
    'entries' é uma lista de dicts (linhas JSON parseadas).
    """
    path = _find_claude_session_file(session_uuid)
    if not path:
        return ([], None)

    entries: list[dict[str, Any]] = []
    model: Optional[str] = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = (raw or "").strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                # mantém o viewer robusto
                entries.append(
                    {
                        "type": "system",
                        "level": "error",
                        "timestamp": _safe_iso_from_mtime(path),
                        "error": "Linha inválida (JSONL) em sessão claude",
                        "raw": line[:500],
                    }
                )
                continue

            if model is None:
                msg = item.get("message")
                if isinstance(msg, dict):
                    m = msg.get("model")
                    if isinstance(m, str) and m.strip():
                        model = m.strip()
            entries.append(item)

    return (entries, model)

# Servir arquivos estáticos do chat-simples (sempre funciona, mesmo rodando de backend-dados/)
app.mount("/css", StaticFiles(directory=str(CHAT_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(CHAT_DIR / "js")), name="js")
app.mount("/html", StaticFiles(directory=str(CHAT_DIR / "html")), name="html")

app.include_router(logs_router)

# ========== ARMAZENAMENTO DE HISTÓRICO EM MEMÓRIA ==========
# Dicionário para armazenar históricos por conversation_id
# Estrutura: {conversation_id: [{"user": "...", "ai": "...", "progresso": {...}, "quick_replies": [...]}, ...]}
conversation_histories = {}

# Limite de históricos armazenados (evita uso excessivo de memória)
MAX_HISTORIES = 1000

def get_or_create_history(conversation_id):
    """Recupera histórico existente ou cria novo"""
    if conversation_id not in conversation_histories:
        conversation_histories[conversation_id] = []

        # Remove históricos mais antigos se exceder limite
        if len(conversation_histories) > MAX_HISTORIES:
            oldest_key = list(conversation_histories.keys())[0]
            del conversation_histories[oldest_key]

    return conversation_histories[conversation_id]

# 🔐 Autenticação
SECRET_KEY = "segredo-teste"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash pré-computado da senha "N4nd@M4c#2025" (evita erro bcrypt durante import)
# Use: pwd_context.hash("N4nd@M4c#2025") para gerar novo hash se necessário
fake_users = {"aluno1": "$2b$12$kQ8ZqX5y6rC9vD2nH0jO0OeKZqXxYwZqXxYwZqXxYwZqXxYwZqXxYO"}

def authenticate_user(username: str, password: str):
    if username not in fake_users:
        return False
    return pwd_context.verify(password, fake_users[username])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.get("/")
def root():
    """Redireciona para o chat-simples"""
    return RedirectResponse(url="/html/index.html")

# ---------- Helper de interpretação de módulo/aula (NÃO altera a lógica dos módulos) ----------
_MOD_RE = re.compile(r"\bm[óo]dulo\s*0*(\d{1,2})\b", re.IGNORECASE)
_AULA_RE = re.compile(r"\baula\s*0*(\d{1,2})(?:\.(\d{1,2}))?(?:\.(\d{1,2}))?\b", re.IGNORECASE)
_CURTA_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{1,2}))?\b")

def _normalizar_comando_modulo_aula(texto: str):
    """
    Converte pedidos livres para forma canônica entendida pelo generate_answer:
      - "quero o módulo 07" -> "módulo 7"
      - "aula 7.2.2" / "7.2.2" -> "aula 7.2.2"
      - "módulo 7 aula 02.03" -> "módulo 7, aula 2.3"
    Sem detecção: retorna None para não interferir no restante.
    """
    if not isinstance(texto, str):
        return None
    t = texto.strip().lower()

    modulo = None
    aula_str = None

    m = _MOD_RE.search(t)
    if m:
        modulo = int(m.group(1))

    a = _AULA_RE.search(t)
    if a:
        partes = [p for p in a.groups() if p]
        aula_str = ".".join(str(int(p)) for p in partes)

    if aula_str is None:
        c = _CURTA_RE.search(t)
        if c:
            partes = [p for p in c.groups() if p]
            aula_str = ".".join(str(int(p)) for p in partes)

    # Frases como "ver módulo 7" que não pegam pelo acento
    if modulo is None and ("módulo" in t or "modulo" in t):
        n = re.search(r"\b0*(\d{1,2})\b", t)
        if n:
            modulo = int(n.group(1))

    if modulo is None and aula_str is None:
        return None

    if modulo is not None and aula_str:
        return f"módulo {modulo}, aula {aula_str}"
    if modulo is not None:
        return f"módulo {modulo}"
    return f"aula {aula_str}"
# -----------------------------------------------------------------------------------------------

def _parece_lista_modulos(texto: str) -> bool:
    """Heurística leve para detectar quando a resposta voltou com a lista de módulos."""
    if not isinstance(texto, str):
        return False
    t = texto.lower()
    return ("composto por 7 módulos" in t) or ("módulo 01" in t and "módulo 07" in t)

# ====== ENDPOINT WEBSOCKET PARA CHAT-SIMPLES ======
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Endpoint WebSocket para streaming de respostas compatível com chat-simples"""
    await websocket.accept()
    print("✅ WebSocket conectado")

    conversation_id = None

    # Task de keepalive para manter conexão ativa
    async def send_keepalive():
        while True:
            try:
                await asyncio.sleep(30)  # Ping a cada 30 segundos
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    keepalive_task = asyncio.create_task(send_keepalive())

    try:
        while True:
            # Recebe mensagem do cliente
            data = await websocket.receive_json()

            # Responde pong se for ping do cliente
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Ignora pong do cliente
            if data.get("type") == "pong":
                continue
            print(f"📨 Mensagem recebida: {data}")
            question = data.get("message", "")
            conversation_id = data.get("conversation_id", conversation_id)

            if not question:
                continue

            # Gera conversation_id se não existir
            if not conversation_id:
                conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Recupera ou cria histórico para esta conversa
            conversation_history = get_or_create_history(conversation_id)

            # Envia confirmação de que mensagem do usuário foi salva
            await websocket.send_json({
                "type": "user_message_saved",
                "conversation_id": conversation_id
            })

            # Adiciona pergunta ao histórico
            conversation_history.append({"user": question, "ai": ""})

            # Recupera contexto
            context = retrieve_relevant_context(question)
            tipo_de_prompt = inferir_tipo_de_prompt(question)

            # Gera resposta com streaming
            full_response = ""
            quick_replies = []
            progresso = None
            start_time = datetime.now()
            is_first = len(conversation_history) == 1

            try:
                async for item in generate_answer_stream(
                    question=question,
                    context=context,
                    history=conversation_history[:-1],
                    tipo_de_prompt=tipo_de_prompt,
                    is_first_question=is_first
                ):
                    item_type = item.get("type")
                    item_data = item.get("data")

                    if item_type == "metadata":
                        # Metadados (progresso, cenário) - não precisa enviar ao cliente
                        progresso = item_data.get("progresso")
                        continue

                    elif item_type == "text":
                        # Chunk de texto - envia ao cliente
                        text_chunk = item_data
                        full_response += text_chunk
                        await websocket.send_json({
                            "type": "text_chunk",
                            "content": text_chunk
                        })

                    elif item_type == "complete":
                        # Dados de conclusão
                        quick_replies = item_data.get("quick_replies", [])
                        if "full_response" in item_data:
                            full_response = item_data["full_response"]
                        if "progresso" in item_data:
                            progresso = item_data["progresso"]

                # Calcula duração
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # Atualiza histórico com resposta completa e progresso
                conversation_history[-1]["ai"] = full_response
                if progresso:
                    conversation_history[-1]["progresso"] = progresso
                if quick_replies:
                    conversation_history[-1]["quick_replies"] = quick_replies

                # Envia resultado final (formato compatível com chat-simples)
                await websocket.send_json({
                    "type": "result",
                    "content": full_response,
                    "conversation_id": conversation_id,
                    "duration_ms": duration_ms,
                    "num_turns": len(conversation_history),
                    "quick_replies": quick_replies,
                    "progresso": progresso
                })

                # Log da conversa
                registrar_log(
                    usuario=f"ws_{conversation_id}",
                    pergunta=question,
                    resposta=full_response,
                    contexto=context,
                    tipo_prompt=tipo_de_prompt,
                    modulo=str(progresso.get("modulo")) if progresso else None,
                    aula=progresso.get("aula") if progresso else None
                )

            except Exception as e:
                print(f"❌ Erro ao gerar resposta: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": f"Erro ao processar sua mensagem: {str(e)}"
                })

    except WebSocketDisconnect:
        print(f"Cliente desconectado (conversation_id: {conversation_id})")
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": "Erro interno do servidor"
            })
        except:
            pass
        await websocket.close()
    finally:
        keepalive_task.cancel()  # Cancela task de keepalive

# ====== ENDPOINTS REST PARA HISTÓRICO (OPCIONAL) ======

@app.get("/api/conversation/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """Recupera histórico de uma conversa específica"""
    history = conversation_histories.get(conversation_id, [])
    return JSONResponse({
        "conversation_id": conversation_id,
        "messages": history,
        "count": len(history)
    })

@app.get("/api/conversations")
async def list_conversations():
    """Lista todas as conversas ativas"""
    conversations = [
        {
            "conversation_id": conv_id,
            "message_count": len(messages),
            "last_message": messages[-1] if messages else None
        }
        for conv_id, messages in conversation_histories.items()
    ]
    return JSONResponse({
        "conversations": conversations,
        "total": len(conversations)
    })

# ====== ENDPOINTS "SESSIONS" PARA A UI DE HISTÓRICO (chat-simples) ======
# A UI do histórico (index_projects.html / session-viewer.html) espera rotas /sessions.
# Aqui mapeamos essas "sessions" para os registros persistidos em logs.db.

def _session_usernames(session_id: str) -> list[str]:
    # Compatibilidade: nós salvamos como usuario="ws_<conversation_id>"
    if not session_id:
        return []
    return [session_id, f"ws_{session_id}"]

def _normalize_session_id(usuario: str) -> str:
    if isinstance(usuario, str) and usuario.startswith("ws_"):
        return usuario[len("ws_"):]
    return usuario

@app.get("/sessions")
def list_sessions():
    """
    Lista sessões persistidas em logs.db.
    Retorna no formato esperado pela página chat-simples/html/index_projects.html.
    """
    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)
    hidden_ids = _get_hidden_session_ids(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT usuario, MAX(data) as updated_at, COUNT(*) as message_count
        FROM logs
        GROUP BY usuario
        ORDER BY updated_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    sessions: list[dict[str, Any]] = []
    for usuario, updated_at, message_count in rows:
        sid = _normalize_session_id(usuario)
        if sid in hidden_ids:
            continue

        # Buscar metadados da sessão
        conn = sqlite3.connect(LOGS_DB_PATH)
        metadata = _get_session_metadata(conn, sid)
        conn.close()

        sessions.append(
            {
                "session_id": sid,
                "file_name": sid,  # compatibilidade com UI
                "file": str(BASE_DIR / "logs.db"),  # usado pela UI para inferir "projeto"
                "updated_at": updated_at,
                "message_count": int(message_count or 0),
                "model": "MiniMax-M2",
                "title": metadata.get('title'),
                "summary": metadata.get('summary'),
            }
        )

    # Sessões do Claude Code (Cursor/Claude CLI) em ~/.claude/projects
    for jsonl_path in _iter_claude_project_jsonl_files():
        if not _should_include_claude_jsonl(jsonl_path):
            continue
        session_uuid = jsonl_path.stem
        session_id = f"{CLAUDE_SESSION_PREFIX}{session_uuid}"
        if session_id in hidden_ids:
            continue
        inferred_label = _infer_claude_label_from_jsonl(jsonl_path)

        # Buscar metadados da sessão
        conn = sqlite3.connect(LOGS_DB_PATH)
        metadata = _get_session_metadata(conn, session_id)
        conn.close()

        sessions.append(
            {
                "session_id": session_id,
                "file_name": jsonl_path.name,
                "file": str(jsonl_path),
                "updated_at": _safe_iso_from_mtime(jsonl_path),
                "message_count": _count_jsonl_lines(jsonl_path),
                "model": "Claude Code",
                "label": inferred_label,
                "title": metadata.get('title'),
                "summary": metadata.get('summary'),
            }
        )

    # Ordena por updated_at (desc) — suporta ISO e timestamps do sqlite
    try:
        sessions.sort(key=lambda s: str(s.get("updated_at") or ""), reverse=True)
    except Exception:
        pass

    return JSONResponse({"count": len(sessions), "sessions": sessions})

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """
    Retorna "mensagens" da sessão em um formato que o session-viewer.html consegue renderizar.
    Cada registro de logs vira 2 entradas: user (pergunta) e assistant (resposta).
    """
    # Sessões do Claude Code (JSONL em ~/.claude/projects)
    if isinstance(session_id, str) and session_id.startswith(CLAUDE_SESSION_PREFIX):
        claude_uuid = session_id.split(CLAUDE_SESSION_PREFIX, 1)[1]
        entries, model = _load_claude_session_entries(claude_uuid)
        path = _find_claude_session_file(claude_uuid)
        meta_timestamp = _safe_iso_from_mtime(path) if path else datetime.utcnow().isoformat()
        meta = {
            "type": "meta",
            "timestamp": meta_timestamp,
            "message": {
                "model": model or "unknown",
                "source": "claude_projects",
                "file": str(path) if path else None,
            },
        }
        messages = [meta, *entries]
        return JSONResponse({"session_id": session_id, "count": len(messages), "messages": messages})

    usernames = _session_usernames(session_id)
    if not usernames:
        return JSONResponse({"error": "session_id inválido"}, status_code=400)

    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, pergunta, resposta, data
        FROM logs
        WHERE usuario IN (?, ?)
        ORDER BY id ASC
        """,
        (usernames[0], usernames[1]),
    )
    rows = cursor.fetchall()
    conn.close()

    messages: list[dict[str, Any]] = []
    # Entrada "meta" só para o viewer conseguir mostrar o model facilmente
    messages.append(
        {
            "type": "meta",
            "timestamp": rows[0][3] if rows else datetime.utcnow().isoformat(),
            "message": {"model": "MiniMax-M2"},
        }
    )

    for log_id, pergunta, resposta, data in rows:
        msg_id = f"log:{log_id}"
        if pergunta:
            messages.append(
                {
                    "id": msg_id,
                    "role": "user",
                    "content": pergunta,
                    "timestamp": data,
                }
            )
        if resposta:
            messages.append(
                {
                    "id": msg_id,
                    "role": "assistant",
                    "content": resposta,
                    "timestamp": data,
                }
            )

    return JSONResponse({"session_id": session_id, "count": len(messages), "messages": messages})

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """
    Remove uma sessão.
    - Para 'claude:<uuid>': deleta o arquivo JSONL em ~/.claude/projects.
    - Para sessões do logs.db: deleta registros (comportamento anterior).
    """
    if isinstance(session_id, str) and session_id.startswith(CLAUDE_SESSION_PREFIX):
        claude_uuid = session_id.split(CLAUDE_SESSION_PREFIX, 1)[1]
        jsonl_path = _find_claude_session_file(claude_uuid)
        if not jsonl_path or not jsonl_path.exists():
            return JSONResponse({"success": False, "error": "Sessão do Claude Code não encontrada."}, status_code=404)
        if not _is_safe_claude_session_path(jsonl_path):
            return JSONResponse({"success": False, "error": "Caminho inválido para exclusão."}, status_code=400)
        try:
            jsonl_path.unlink()
        except Exception as e:
            return JSONResponse({"success": False, "error": f"Falha ao deletar arquivo: {e}"}, status_code=500)
        return JSONResponse({"success": True, "deleted": 1, "action": "deleted_file"})

    usernames = _session_usernames(session_id)
    if not usernames:
        return JSONResponse({"success": False, "error": "session_id inválido"}, status_code=400)

    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs WHERE usuario IN (?, ?)", (usernames[0], usernames[1]))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "deleted": deleted})

@app.post("/sessions/{session_id}/summary")
def generate_session_summary(session_id: str, request: Request):
    """
    Gera resumo da sessão usando LLM.
    """
    from gpt_utils import generate_conversation_summary

    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)

    # Extrair mensagens da sessão
    messages = []
    if isinstance(session_id, str) and session_id.startswith(CLAUDE_SESSION_PREFIX):
        # Sessão do Claude Code (JSONL)
        claude_uuid = session_id.split(CLAUDE_SESSION_PREFIX, 1)[1]
        entries, model = _load_claude_session_entries(claude_uuid)
        # Converter para formato esperado pela função de resumo
        for entry in entries:
            if entry.get('type') == 'message':
                msg = entry.get('message', {})
                role = 'assistant' if msg.get('role') == 'assistant' else 'user'
                content = msg.get('content', {})
                # Extrair texto do conteúdo
                if isinstance(content, dict):
                    text = content.get('text', '')
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                if text:
                    messages.append({'role': role, 'content': text})
    else:
        # Sessão do logs.db (WebSocket)
        usernames = _session_usernames(session_id)
        if usernames:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usuario, pergunta, resposta, data FROM logs WHERE usuario IN (?, ?) ORDER BY data ASC",
                (usernames[0], usernames[1])
            )
            rows = cursor.fetchall()
            for usuario, pergunta, resposta, data in rows:
                if pergunta:
                    messages.append({'role': 'user', 'content': pergunta})
                if resposta:
                    messages.append({'role': 'assistant', 'content': resposta})

    conn.close()

    # Gerar resumo
    summary = generate_conversation_summary(messages, max_length=500)

    # Salvar resumo no session_meta
    conn = sqlite3.connect(LOGS_DB_PATH)
    _save_session_metadata(conn, session_id, summary=summary)
    conn.close()

    return JSONResponse({"success": True, "summary": summary})

@app.put("/sessions/{session_id}/metadata")
def save_session_metadata(session_id: str, request: Request):
    """
    Salva metadados da sessão (título, resumo, tags).
    """
    try:
        payload = request.json()
        title = payload.get('title')
        summary = payload.get('summary')
        tags = payload.get('tags')

        conn = sqlite3.connect(LOGS_DB_PATH)
        _save_session_metadata(conn, session_id, title=title, summary=summary, tags=tags)
        conn.close()

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/sessions/{session_id}/metadata")
def get_session_metadata(session_id: str):
    """
    Recupera metadados da sessão.
    """
    conn = sqlite3.connect(LOGS_DB_PATH)
    metadata = _get_session_metadata(conn, session_id)
    conn.close()

    if not metadata:
        return JSONResponse({"success": False, "error": "Metadados não encontrados"}, status_code=404)

    return JSONResponse({"success": True, "metadata": metadata})

@app.delete("/sessions/{session_id}/messages")
async def delete_session_message(session_id: str, request: Request):
    """
    Remove uma entrada do histórico.
    Compatível com o payload do session-viewer.html: {message_id} ou {line_index}.
    Observação: aqui removemos por "log id" (apaga pergunta+resposta daquele turno).
    """
    usernames = _session_usernames(session_id)
    if not usernames:
        return JSONResponse({"success": False, "error": "session_id inválido"}, status_code=400)

    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    message_id = payload.get("message_id")
    line_index = payload.get("line_index")

    target_log_id: Optional[int] = None

    if isinstance(message_id, str) and message_id.strip():
        mid = message_id.strip()
        if mid.startswith("log:"):
            mid = mid.split("log:", 1)[1]
        try:
            target_log_id = int(mid)
        except Exception:
            target_log_id = None

    if target_log_id is None and isinstance(line_index, int):
        # Reconstrói o mapping: messages[0] é meta; depois pares (user/assistant) por log
        if line_index <= 0:
            return JSONResponse({"success": False, "error": "line_index inválido"}, status_code=400)
        entry_index = line_index - 1
        log_offset = entry_index // 2

        conn = sqlite3.connect(LOGS_DB_PATH)
        _ensure_logs_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM logs
            WHERE usuario IN (?, ?)
            ORDER BY id ASC
            LIMIT 1 OFFSET ?
            """,
            (usernames[0], usernames[1], log_offset),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            target_log_id = int(row[0])

    if target_log_id is None:
        return JSONResponse({"success": False, "error": "Não foi possível identificar a mensagem."}, status_code=400)

    conn = sqlite3.connect(LOGS_DB_PATH)
    _ensure_logs_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM logs WHERE id = ? AND usuario IN (?, ?)",
        (target_log_id, usernames[0], usernames[1]),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted <= 0:
        return JSONResponse({"success": False, "error": "Mensagem não encontrada."}, status_code=404)

    return JSONResponse({"success": True, "deleted": deleted, "log_id": target_log_id})

# =============== DASHBOARD LOGS (DESABILITADO - template removido) =================
# O dashboard foi desabilitado pois o template dashboard.html foi removido junto com a pasta templates/
# Para reativar, crie um template HTML ou use uma página estática em chat-simples/html/

# DATABASE_URL = "sqlite:///logs.db"
# engine = create_engine(DATABASE_URL)
#
# def get_current_admin_user():
#     return True
#
# @app.get("/dashboard", response_class=HTMLResponse)
# async def dashboard(request: Request, user=Depends(get_current_admin_user)):
#     # ... código comentado pois precisa de template

# @app.get("/dashboard/export", response_class=StreamingResponse)
# async def dashboard_export(request: Request, user=Depends(get_current_admin_user)):
#     # ... código comentado pois depende do dashboard desabilitado
#     # Use logs_route.py para exportação de logs

# =============== FIM DASHBOARD LOGS ===================
