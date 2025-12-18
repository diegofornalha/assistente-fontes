# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão Geral do Projeto

Este é um chatbot educacional em português brasileiro chamado "Assistente Professor" para o curso "Consultório High Ticket". A aplicação funciona como uma professora virtual (Nanda Mac.ia) que ensina e tira dúvidas de profissionais da saúde sobre como atrair pacientes high ticket e aumentar o faturamento de seus consultórios.

### Stack Tecnológico
- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 Templates + HTML
- **Autenticação**: JWT (python-jose) + bcrypt (passlib)
- **IA/LLM**: Minimax abab6.5s-chat (compatível com OpenAI SDK)
- **Busca Semântica**: LlamaIndex + FAISS (vector store local)
- **Embeddings**: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) - local e gratuito
- **Banco de Dados**: SQLite (logs.db)
- **Deploy**: Render (plataforma PaaS)

## Comandos Essenciais

### Desenvolvimento Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor de desenvolvimento
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Inicializar banco de dados de logs
python init_db.py

# Gerar/regenerar índice de busca vetorial
python generate_index.py

# Debug de transcrições
python debug_transcricoes.py
```

### Deploy (Render)
O deploy é automático via Render quando há push na branch `main`:
```bash
# Build: pip install -r requirements.txt
# Start: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Variáveis de Ambiente Necessárias
```
MINIMAX_API_KEY=<sua-chave-minimax>  # Para chat/completions (obrigatório)
```

**Nota:** O projeto usa Minimax para respostas de chat e sentence-transformers (HuggingFace) para embeddings. Não é mais necessário OPENAI_API_KEY.

## Arquitetura do Sistema

### Fluxo Principal (main.py)

1. **Autenticação** (`/login`)
   - Usuário: `aluno1`
   - Senha: `N4nd@M4c#2025`
   - Token JWT armazenado em cookie httponly

2. **Interface de Chat** (`/chat`)
   - Template: `templates/chat.html`
   - Histórico de conversa mantido via Form POST
   - Quick replies gerados dinamicamente

3. **Processamento de Perguntas** (`POST /ask`)
   - Normalização de comandos de módulo/aula (regex)
   - Recuperação de contexto via `search_engine.py`
   - Inferência de tipo de prompt via `prompt_router.py`
   - Geração de resposta via `gpt_utils.py`
   - Logging em SQLite via `db_logs.py`
   - Renderização de Markdown para HTML

4. **Dashboard Administrativo** (`/dashboard`)
   - Visualização e filtragem de logs
   - Estatísticas de uso
   - Exportação CSV (`/dashboard/export`)

### Módulos Principais

**gpt_utils.py**: Lógica central de conversação
- Gerencia sistema de progressão por módulos/aulas (7 módulos)
- Detecta cenários: dúvida pontual, exemplo prático, navegação, curso completo
- Mantém estado de progresso (módulo, aula, etapa 1-3, aguardando_duvida)
- Gera quick replies contextuais
- Chamadas à API Minimax (abab6.5s-chat, temperature 0.4, max_tokens 900)

**search_engine.py**: Busca semântica RAG
- Carrega/constrói índice FAISS de `transcricoes.txt`
- Usa LlamaIndex para embeddings + retrieval
- Filtra contextos fora de escopo (marketing digital, redes sociais)
- Configurável: top_k=3, chunk_size=512

**prompt_router.py**: Classificação de intenção
- Identifica tipo de prompt: health_plan, precificacao, mensagem_automatica, aplicacao, correcao, revisao, faq, explicacao
- Usado para personalizar instruções ao GPT e logging

**auth_utils.py**: Middleware de autenticação
- Valida JWT em cookies
- Redireciona para /login se inválido

**db_logs.py**: Persistência de logs
- Registra: usuario, pergunta, resposta, contexto, tipo_prompt, modulo, aula, timestamp
- SQLite (logs.db)

**healthplan_log.py**: Log específico de Health Plan
- Rastreamento separado de perguntas sobre planos de tratamento

### Sistema de Progressão de Conteúdo

O curso tem **7 módulos** com aulas numeradas (ex: 1.1, 2.3, 7.9):
- Módulo 1: 5 aulas (1.1 a 1.5)
- Módulo 2: 9 aulas (2.1 a 2.9)
- Módulo 3: 5 aulas
- Módulo 4: 5 aulas
- Módulo 5: 5 aulas
- Módulo 6: 5 aulas
- Módulo 7: 9 aulas (especialidades)

**Lógica de Progressão**:
- Cada aula tem 3 etapas (introdução, prática, conclusão)
- Sistema de navegação: próxima/anterior aula, repetir, voltar, escolher módulo/aula
- Respostas "sim"/"não" controlam fluxo (avançar etapa vs pular aula)
- Normalização automática de comandos: "módulo 07" → "módulo 7", "aula 7.2.2" → "aula 7.2.2"

### Detecção Especial de Cenários

**Anti-loop de lista de módulos** (main.py:196-207):
- Se usuário pede módulo/aula específica mas GPT retorna lista geral, faz retry com reforço
- Usa heurística: verifica se resposta contém "composto por 7 módulos"

**Dúvidas pontuais** (gpt_utils.py:59-104):
- Detecta especialidades médicas (dermatologista, pediatra, psicóloga, etc.)
- Detecta termos de ação (atrair, captar, faturar, consultório cheio, etc.)
- Retorna resposta personalizada sem entrar na progressão de aulas

## Convenções de Código

### Normalização de Histórico
- Remove tags HTML de respostas anteriores antes de enviar ao GPT
- Preserva campos: user, ai, quick_replies, chip, progresso

### Prompt Engineering
- Sempre cita módulo/aula com nome exato (não adaptar/resumir)
- Inclui `BLOCO_MODULOS` (estrutura completa do curso) em todo prompt
- Instrução: "Responda SEMPRE em português do Brasil"
- Temperature: 0.4 (balance entre criatividade e consistência)

### Tratamento de Erros
- Exceptions da API Minimax → retorna `OUT_OF_SCOPE_MSG` com log de erro
- Exceptions genéricas → retorna `OUT_OF_SCOPE_MSG`
- Quick replies vazios em caso de erro

### Segurança
- SECRET_KEY hardcoded como "segredo-teste" (⚠️ usar env var em produção)
- Senhas hasheadas com bcrypt
- JWT expira em 60 minutos

## Estrutura de Arquivos Importantes

```
/templates/
  - login.html       # Tela de login
  - chat.html        # Interface do chat
  - dashboard.html   # Dashboard administrativo

transcricoes.txt     # Base de conhecimento (transcrições do curso)
storage/             # Índice FAISS gerado por generate_index.py
logs.db              # Banco SQLite de logs
render.yaml          # Configuração de deploy no Render
requirements.txt     # Dependências Python
constraints.txt      # Constraints de versões de pacotes
```

## Notas Importantes para Desenvolvimento

1. **Regenerar índice**: Executar `python generate_index.py` após modificar `transcricoes.txt`
2. **História do chat**: É mantida como JSON serializado em campo hidden do formulário (não em sessão/cookie)
3. **Markdown**: Respostas são convertidas de Markdown para HTML usando `markdown2` antes de exibir
4. **Logs estruturados**: Todo POST em `/ask` gera log em SQLite
5. **FAISS local**: Não usa serviço externo de vector store (roda em CPU)
6. **Embeddings locais**: Usa sentence-transformers (HuggingFace) - não requer API key externa
7. **LlamaIndex >= 0.12.43**: Versão crítica para compatibilidade

## Limitações Conhecidas

- Autenticação simplificada (fake_users em memória)
- SECRET_KEY hardcoded
- Sem paginação no dashboard
- Histórico de chat não persistido (perdido ao recarregar página)
- Índice FAISS reconstruído do zero se deletar pasta `storage/`
