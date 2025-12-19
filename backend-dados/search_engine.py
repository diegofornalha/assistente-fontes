import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import (
    SimpleDirectoryReader,
    GPTVectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Carrega variáveis do .env
load_dotenv()

# Caminhos absolutos (não dependem do diretório atual ao rodar o uvicorn)
BASE_DIR = Path(__file__).resolve().parent.parent      # /assistente-fontes
BACKEND_DIR = Path(__file__).resolve().parent          # /assistente-fontes/backend-dados

# 📁 Diretório e caminho do índice
INDEX_DIR = str(BASE_DIR / "storage")
INDEX_FILE = str(Path(INDEX_DIR) / "index.json")
TRANSCRICOES_PATH = str(BACKEND_DIR / "transcricoes.txt")

# 🤖 Define o modelo de embedding (sentence-transformers local, gratuito)
# Usa modelo multilíngue otimizado para português
Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def load_or_build_index():
    """Carrega o índice existente ou cria um novo a partir de transcricoes.txt."""
    if os.path.exists(INDEX_FILE):
        print("📁 Índice encontrado. Carregando do disco...")
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_DIR)
        return load_index_from_storage(storage_context)
    else:
        print("⚙️ Índice não encontrado. Construindo novo...")
        docs = SimpleDirectoryReader(input_files=[TRANSCRICOES_PATH]).load_data()
        index = GPTVectorStoreIndex.from_documents(docs)
        index.storage_context.persist(persist_dir=INDEX_DIR)
        print(f"✅ Índice construído com {len(docs)} documentos.")
        return index

# ⚡ Inicializa o índice na importação deste módulo
index = load_or_build_index()

def retrieve_relevant_context(
    question: str,
    top_k: int = 3,
    chunk_size: int = 512
) -> str:
    """
    Busca no índice até `top_k` trechos que respondam à `question`.
    Usa `chunk_size` para controlar o tamanho dos blocos de texto.
    Retorna string vazia se não encontrar algo relevante.
    """
    # DEBUG: confira nos logs qual pergunta chegou
    print("🔎 DEBUG — Pergunta para contexto:", question)

    # Usa retriever em vez de query_engine (não precisa de LLM)
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(question)

    # Combina os textos dos nodes recuperados
    if not nodes:
        print("🔎 DEBUG — Nenhum nó recuperado")
        return ""

    response_str = "\n\n".join([node.text for node in nodes])
    # DEBUG: confira o texto bruto retornado
    print("🔎 DEBUG — Contexto bruto retornado:", response_str[:200] + "...")

    lower = response_str.lower()
    # se vazio ou sem sentido
    if not lower or lower in ("none", "null"):
        print("🔎 DEBUG — Contexto vazio após normalização")
        return ""

    # bloqueia respostas genéricas
    for frase in ("não tenho certeza", "desculpe", "não sei"):
        if frase in lower:
            print("🔎 DEBUG — Contexto bloqueado por frase de incerteza")
            return ""

    # filtra termos fora de escopo
    proibidos = [
        "instagram", "vídeos para instagram", "celular para gravar", "smartphone",
        "tiktok", "post viral", "gravar vídeos", "microfone", "câmera",
        "edição de vídeo", "hashtags", "stories", "marketing de conteúdo",
        "produção de vídeo", "influencer"
    ]
    if any(tp in lower for tp in proibidos):
        print("🔎 DEBUG — Contexto bloqueado por termo proibido")
        return ""

    # DEBUG: contexto aprovado
    print("🔎 DEBUG — Contexto final aceito:", response_str)
    return response_str
