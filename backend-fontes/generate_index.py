import os
import shutil
from llama_index.core import (
    SimpleDirectoryReader,
    GPTVectorStoreIndex,
    Settings
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Caminho de saída
INDEX_DIR = "storage"

# Apaga índice antigo (importante!)
if os.path.exists(INDEX_DIR):
    print("🧹 Limpando índice anterior...")
    shutil.rmtree(INDEX_DIR)

# Define o modelo de embedding (sentence-transformers local, gratuito)
# Usa modelo multilíngue otimizado para português
Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Lê os dados da transcrição
print("📄 Lendo o arquivo transcricoes.txt...")
documents = SimpleDirectoryReader(input_files=["transcricoes.txt"]).load_data()

# Gera o índice
print("⚙️ Gerando o índice vetorial...")
index = GPTVectorStoreIndex.from_documents(documents)

# Persiste no diretório
print(f"💾 Salvando índice em: {INDEX_DIR}")
index.storage_context.persist(persist_dir=INDEX_DIR)

print("✅ Índice criado com sucesso.")
