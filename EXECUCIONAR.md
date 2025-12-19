# Como Executar o Assistente de Fontes

## Pré-requisitos
- Python 3.13+ instalado
- Dependências instaladas no ambiente virtual

## Passos para Executar

### 1. Navegar para o diretório do backend
```bash
cd /home/fontes/assistente-fontes/backend-dados
```

### 2. Ativar o ambiente virtual
```bash
source ../.venv/bin/activate
```

### 3. Executar o servidor
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8181
```

## Acesso à Aplicação

Após executar os comandos acima, a aplicação estará disponível em:
- **URL Local**: http://localhost:8181/
- **WebSocket Chat**: ws://localhost:8181/ws/chat

## Credenciais de Acesso

- **Usuário**: `aluno1`
- **Senha**: `N4nd@M4c#2025`

## Estrutura dos Diretórios

```
/home/fontes/assistente-fontes/
├── backend-dados/          # Código do servidor FastAPI
│   ├── main.py             # Arquivo principal
│   ├── search_engine.py    # Motor de busca semântica
│   ├── gpt_utils.py        # Integração com IA
│   └── ...
├── chat-simples/           # Interface web
│   ├── html/               # Templates HTML
│   ├── css/                # Estilos
│   └── js/                 # Scripts JavaScript
├── storage/                # Índice FAISS (busca vetorial)
└── .venv/                  # Ambiente virtual Python
```

## Notas Importantes

### Primeira Execução
Na primeira execução, o sistema irá:
1. ⚙️ Construir o índice de busca vetorial (FAISS)
2. ✅ Criar o índice com 1 documento (transcricoes.txt)

### Dependências

Se houver erro de dependências, reinstale com:
```bash
# No diretório /home/fontes/assistente-fontes
pip install -r requirements.txt
```

### Logs e Monitoramento

- O servidor roda na porta 8181
- Logs são exibidos no terminal
- Histórico de conversas salvo em `logs.db`

### Parar o Servidor

Pressione `Ctrl+C` no terminal onde o servidor está rodando.

## Troubleshooting

### Erro: "No module named 'search_engine'"
- **Solução**: Certifique-se de estar no diretório `/home/fontes/assistente-fontes/backend-dados` antes de executar o uvicorn

### Erro: "Directory 'chat-simples/css' does not exist"
- **Solução**: Execute o comando a partir de `/home/fontes/assistente-fontes/backend-dados` com o ambiente virtual ativado

### Erro: "uvicorn: command not found"
- **Solução**: Ative o ambiente virtual: `source ../.venv/bin/activate`

## Comandos Alternativos

### Execução com PYTHONPATH (diretório raiz)
```bash
cd /home/fontes/assistente-fontes
PYTHONPATH=/home/fontes/assistente-fontes/backend-dados:$PYTHONPATH .venv/bin/python -m uvicorn backend-dados.main:app --reload --host 0.0.0.0 --port 8181
```

### Verificar se a porta está em uso
```bash
netstat -tlnp | grep 8181
```

## Arquitetura do Sistema

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/JS (chat-simples)
- **IA**: MiniMax abab6.5s-chat
- **Busca**: FAISS + LlamaIndex
- **Banco**: SQLite (logs.db)
- **WebSocket**: Para chat em tempo real

---

**Última atualização**: 2025-12-12
