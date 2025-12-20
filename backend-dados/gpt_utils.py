import os
import re
import random
from anthropic import Anthropic
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

TRANSCRIPTS_PATH = os.path.join(os.path.dirname(__file__), "transcricoes.txt")

# Aceita token via MINIMAX_API_KEY (padrão) ou ANTHROPIC_AUTH_TOKEN (fallback).
# Obs: o backend usa base_url da MiniMax, então ambos apontam para o mesmo token JWT.
_API_KEY = os.getenv("MINIMAX_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")

# Configuração Minimax via API compatível com Anthropic
client = Anthropic(
    base_url="https://api.minimax.io/anthropic",
    api_key=_API_KEY
)

OUT_OF_SCOPE_MSG = (
    "Desculpe, ainda não tenho informações suficientes sobre esse tema específico. "
    "Por favor, envie outra pergunta ou consulte a documentação disponível."
)

CONTINUE_GUARDRAILS = (
    "IMPORTANTE (tamanho e continuidade): "
    "Se a resposta ficar longa, entregue em partes. "
    "Conclua a PARTE atual de forma completa (não deixe itens numerados/bullets pela metade) "
    "e finalize com a frase: 'Quer que eu continue?' "
    "Não continue automaticamente sem o Doutor(a) pedir."
)

def _looks_truncated(text: str) -> bool:
    """Heurística simples para detectar respostas cortadas (ex.: termina em '2.' ou palavra incompleta)."""
    if not isinstance(text, str):
        return False
    t = text.strip()
    if not t:
        return False

    # Normaliza quebras HTML comuns
    t = t.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n").strip()

    # Termina com marcador de lista sem conteúdo
    for suffix in ("-", "•", "*", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."):
        if t.endswith(suffix):
            return True

    # Último caractere alfanumérico sem pontuação (pode indicar corte)
    last = t[-1]
    if last.isalnum():
        # Se a última "linha" for muito curta e sem pontuação, é suspeito
        last_line = t.splitlines()[-1].strip()
        if last_line and last_line[-1].isalnum() and len(last_line) <= 12:
            return True
    return False

def _should_offer_continue(text: str) -> bool:
    """
    Se a resposta ficou "longa", oferecemos continuação mesmo que não pareça truncada.
    A ideia é padronizar a experiência: longos conteúdos viram "em partes".
    """
    if not isinstance(text, str):
        return False
    t = text.strip()
    if not t:
        return False
    if "Quer que eu continue?" in t:
        return False

    # Normaliza quebras HTML comuns
    t_plain = t.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

    # Heurísticas: tamanho + densidade de estrutura
    if len(t_plain) >= 1400:
        return True

    lines = [ln.strip() for ln in t_plain.splitlines() if ln.strip()]
    if len(lines) >= 18:
        return True

    bullet_lines = sum(1 for ln in lines if ln.startswith(("-", "*", "•")) or re.match(r"^\d+\.\s+", ln))
    if bullet_lines >= 8:
        return True

    headings = sum(1 for ln in lines if re.match(r"^#{1,6}\s+", ln))
    if headings >= 3:
        return True

    return False

def _append_continue_hint(text: str) -> str:
    hint = "\n\n---\n\n**Parece que ainda tem mais conteúdo. Quer que eu continue?**"
    if not isinstance(text, str):
        return hint
    if "Quer que eu continue?" in text:
        return text
    return f"{text.rstrip()}{hint}"

GREETINGS = [
    "Olá! Como posso ajudar você hoje?",
    "Oi! Tudo bem? Em que posso ajudar?",
    "Bem-vindo(a) de volta! Como posso ajudar?",
    "Olá! Estou aqui para ajudar."
]

CLOSINGS = [
    "Ficou com alguma dúvida?",
    "Deseja aprofundar algum ponto ou fazer outra pergunta?",
    "Se quiser, escolha uma opção rápida abaixo ou pergunte de novo!",
    "Se quiser fazer outra pergunta, é só pedir.",
    "Essa resposta foi útil? Clique em 👍 ou 👎."
]

# Estrutura de módulos/aulas removida - sistema agora usa base de conhecimento do transcricoes.txt

def formatar_historico_para_prompt(history):
    """
    Formata o histórico de conversa para ser incluído no prompt da API.
    Remove HTML e campos desnecessários, mantendo apenas user/ai.
    """
    if not history or not isinstance(history, list):
        return "Nenhuma conversa anterior."

    import re
    linhas = []
    for i, item in enumerate(history[-5:]):  # Pega apenas últimas 5 interações para não estourar tokens
        user_msg = item.get('user', '')
        ai_msg = item.get('ai', '')

        # Remove tags HTML das mensagens
        user_msg = re.sub(r'<[^>]+>', '', user_msg).strip()
        ai_msg = re.sub(r'<[^>]+>', '', ai_msg).strip()

        if user_msg:
            linhas.append(f"Usuário: {user_msg}")
        if ai_msg:
            linhas.append(f"Assistente: {ai_msg}")
            linhas.append("")  # Linha em branco entre turnos

    return "\n".join(linhas) if linhas else "Nenhuma conversa anterior."

def gerar_quick_replies(question, explicacao, history=None, progresso=None):
    opcoes = ["Tenho outra dúvida", "Aprofundar este tópico"]
    if isinstance(explicacao, str) and "Quer que eu continue?" in explicacao:
        # Ajuda o usuário a pedir continuação explicitamente
        opcoes.insert(0, "Continuar")
    return opcoes

def resposta_link(titulo, url, icone="📄"):
    return f"<br><a class='chip' href='{url}' target='_blank'>{icone} {titulo}</a>"

def resposta_link_externo(titulo, url, icone="🔗"):
    return f"<br><a class='chip' href='{url}' target='_blank'>{icone} {titulo}</a>"

# Detecção de cenários simplificada
def detectar_cenario(pergunta: str) -> str:
    pergunta = pergunta.lower()
    
    # Detecta perguntas técnicas sobre sistemas, banco de dados, arquitetura
    termos_tecnicos = [
        "data lake", "crm", "supabase", "postgres", "sql", "rls", "policy", "schema",
        "bronze", "silver", "gold", "lead", "evento", "função", "trigger", "tabela"
    ]
    
    if any(t in pergunta for t in termos_tecnicos):
        return "duvida_tecnica"
    
    # Detecta perguntas gerais
    if any(p in pergunta for p in [
        "tenho uma dúvida", "tenho outra dúvida", "minha dúvida", "não entendi", "duvida", "dúvida", "me explica",
        "poderia explicar", "por que", "como", "o que", "quais", "qual", "explique", "me fale", "exemplo", "caso prático",
        "me mostre", "me explique", "?"
    ]):
        return "duvida_pontual"
    elif any(p in pergunta for p in [
        "exemplo prático", "me dá um exemplo", "passo a passo", "como fazer isso", "como faço", "me ensina", "ensinar", "me mostre como"
    ]):
        return "exemplo_pratico"
    else:
        return "geral"

def atualizar_progresso(pergunta: str, progresso: dict) -> dict:
    # Sistema simplificado - não usa mais módulos/aulas
    # Mantém estrutura básica para compatibilidade
    if not progresso:
        return {}
    return progresso

# Base de conhecimento - conteúdo do arquivo transcricoes.txt
# O conteúdo completo está disponível via search_engine que indexa o arquivo transcricoes.txt

def generate_answer(question, context="", history=None, tipo_de_prompt=None, is_first_question=True):
    progresso = {}
    
    saudacao = random.choice(GREETINGS) if is_first_question else ""
    fechamento = random.choice(CLOSINGS)
    cenario = detectar_cenario(question)

    mensagem_generica = question.strip().lower()
    saudacoes_vagas = [
        "olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "pode me ajudar?", "oi, tudo bem?",
        "olá bom dia", "tudo bem?", "tudo certo?", "como vai?", "você pode me ajudar?", "me ajuda?", "olá, boa noite"
    ]
    apresentacoes_vagas = ["meu nome é", "sou ", "me apresentando", "me apresento", "me chamo"]

    # Mensagens vagas ("oi", "tudo bem?") devem ir para a LLM
    is_saudacao = (
        mensagem_generica in saudacoes_vagas
        or any(mensagem_generica.startswith(apr) for apr in apresentacoes_vagas)
    )
    if is_saudacao:
        cenario = "saudacao"

    # Construir instruction baseado no cenário
    if cenario == "saudacao":
        instruction = (
            "O usuário enviou uma saudação/mensagem inicial (ex: 'oi', 'tudo bem?'). "
            "Responda de forma acolhedora e objetiva, explique rapidamente como você pode ajudar com questões sobre "
            "sistemas de CRM, Data Lake, arquitetura de dados, Supabase, PostgreSQL e desenvolvimento de software."
        )
    elif cenario == "duvida_tecnica":
        instruction = (
            "Ótima pergunta técnica!<br>"
            "Forneça uma explicação detalhada e precisa sobre o tema, com exemplos práticos quando possível.<br>"
            "Se quiser aprofundar ou pedir mais exemplos, é só pedir!"
        )
    else:
        instruction = (
            "Ótima pergunta!<br>"
            "Forneça uma explicação detalhada sobre o tema, seguida de exemplos práticos quando possível.<br>"
            "Se quiser aprofundar ou pedir mais exemplos, é só pedir!"
        )

    prompt = f"""{instruction}

{CONTINUE_GUARDRAILS}

Você é um assistente inteligente especializado em ajudar com questões sobre sistemas de CRM, Data Lake, arquitetura de dados e desenvolvimento de software.

Leia atentamente o histórico da conversa antes de responder, compreendendo o contexto exato da interação atual para garantir precisão na sua resposta.

BASE DE CONHECIMENTO DISPONÍVEL:
O sistema possui documentação sobre arquitetura de Data Lake (Bronze → Silver → Gold), CRM inteligente, RLS Policies para Supabase, funções SQL transacionais, e estruturas de banco de dados para sistemas enterprise.

Histórico da conversa anterior:
{formatar_historico_para_prompt(history)}

Pergunta atual do usuário:
'{question}'

Utilize o conteúdo adicional abaixo, se relevante:
{context}
        """
    
    try:
        response = client.messages.create(
            model="MiniMax-M2",
            max_tokens=2048,
            system="Responda SEMPRE em português do Brasil.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        explicacao = response.content[0].text.strip()
        if _looks_truncated(explicacao) or _should_offer_continue(explicacao):
            explicacao = _append_continue_hint(explicacao)
        quick_replies = gerar_quick_replies(question, explicacao, history, progresso)
    except Exception as e:
        print(f"❌ Erro ao chamar Minimax API: {e}")
        explicacao = OUT_OF_SCOPE_MSG
        quick_replies = []
        return explicacao, quick_replies, progresso

    if saudacao:
        resposta = f"{saudacao}<br><br>{explicacao}<br><br>{fechamento}"
    else:
        resposta = f"{explicacao}<br><br>{fechamento}"

    return resposta, quick_replies, progresso


# ========== FUNÇÃO DE STREAMING PARA WEBSOCKET ==========
async def generate_answer_stream(question, context="", history=None, tipo_de_prompt=None, is_first_question=False):
    """
    Versão streaming da generate_answer para uso com WebSocket.
    Yields dicionários com tipo de conteúdo e dados.

    Yields:
        dict: {"type": "metadata"|"text"|"complete", "data": {...}}
    """
    progresso = {}
    cenario = detectar_cenario(question)

    # Envia metadados primeiro (progresso)
    yield {
        "type": "metadata",
        "data": {
            "progresso": progresso,
            "cenario": cenario
        }
    }

    # Detecta mensagens vagas
    mensagem_generica = question.strip().lower()
    saudacoes_vagas = [
        "olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "pode me ajudar?", "oi, tudo bem?",
        "olá bom dia", "tudo bem?", "tudo certo?", "como vai?", "você pode me ajudar?", "me ajuda?", "olá, boa noite"
    ]
    apresentacoes_vagas = ["meu nome é", "sou ", "me apresentando", "me apresento", "me chamo"]
    if mensagem_generica in saudacoes_vagas or any(mensagem_generica.startswith(apr) for apr in apresentacoes_vagas):
        cenario = "saudacao"

    # Constrói o prompt baseado no cenário
    if cenario == "saudacao":
        instruction = (
            "O usuário enviou uma saudação/mensagem inicial (ex: 'oi', 'tudo bem?'). "
            "Responda de forma acolhedora e objetiva, explique rapidamente como você pode ajudar com questões sobre "
            "sistemas de CRM, Data Lake, arquitetura de dados, Supabase, PostgreSQL e desenvolvimento de software."
        )
    elif cenario == "duvida_tecnica":
        instruction = (
            "Ótima pergunta técnica!<br>"
            "Forneça uma explicação detalhada e precisa sobre o tema, com exemplos práticos quando possível.<br>"
        )
    elif cenario in ["duvida_pontual", "exemplo_pratico"]:
        instruction = (
            "Ótima pergunta!<br>"
            "Forneça uma explicação detalhada sobre o tema, seguida de exemplos práticos quando possível.<br>"
        )
    else:
        instruction = ""

    prompt = f"""{instruction}

{CONTINUE_GUARDRAILS}

Você é um assistente inteligente especializado em ajudar com questões sobre sistemas de CRM, Data Lake, arquitetura de dados e desenvolvimento de software.

Leia atentamente o histórico da conversa antes de responder, compreendendo o contexto exato da interação atual para garantir precisão na sua resposta.

BASE DE CONHECIMENTO DISPONÍVEL:
O sistema possui documentação sobre arquitetura de Data Lake (Bronze → Silver → Gold), CRM inteligente, RLS Policies para Supabase, funções SQL transacionais, e estruturas de banco de dados para sistemas enterprise.

Histórico da conversa anterior:
{formatar_historico_para_prompt(history)}

Pergunta atual do usuário:
'{question}'

Utilize o conteúdo adicional abaixo, se relevante:
{context}
    """

    try:
        # Chama Minimax com streaming habilitado (via API Anthropic)
        with client.messages.stream(
            model="MiniMax-M2",
            max_tokens=2048,
            system="Responda SEMPRE em português do Brasil.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        ) as stream:
            # Acumula resposta completa
            full_response = ""

            # Itera pelos chunks da resposta
            for text in stream.text_stream:
                full_response += text
                yield {"type": "text", "data": text}

        if _looks_truncated(full_response) or _should_offer_continue(full_response):
            full_response = _append_continue_hint(full_response)

        # Gera quick_replies baseado na resposta
        quick_replies = gerar_quick_replies(question, full_response, history, progresso)

        # Envia dados de conclusão
        yield {
            "type": "complete",
            "data": {
                "quick_replies": quick_replies,
                "progresso": progresso,
                "full_response": full_response
            }
        }

    except Exception as e:
        print(f"❌ Erro ao fazer streaming da Minimax API: {e}")
        yield {"type": "text", "data": OUT_OF_SCOPE_MSG}
        yield {
            "type": "complete",
            "data": {
                "quick_replies": [],
                "progresso": progresso,
                "error": str(e)
            }
        }

def generate_conversation_summary(messages: list, max_length: int = 500) -> str:
    """
    Gera resumo de uma conversa usando LLM.

    Args:
        messages: Lista de mensagens no formato [{'role': 'user'|'assistant', 'content': '...'}]
        max_length: Comprimento máximo do resumo (padrão: 500 caracteres)

    Returns:
        Resumo formatado da conversa
    """
    if not messages:
        return "Conversa vazia."

    # Extrair texto das mensagens
    conversation_text = ""
    for msg in messages:
        role = msg.get('role', '').lower()
        content = msg.get('content', '').strip()
        if content:
            prefix = "Usuário" if role == 'user' else "Assistente"
            conversation_text += f"{prefix}: {content}\n\n"

    if not conversation_text.strip():
        return "Conversa sem conteúdo textual."

    # Truncar se muito longo (limitar a ~3000 caracteres para o prompt)
    if len(conversation_text) > 3000:
        conversation_text = conversation_text[:3000] + "\n\n[... conversação truncada ...]"

    prompt = f"""
Por favor, crie um resumo conciso desta conversa em português brasileiro.

DIRETRIZES:
- Máximo de {max_length} caracteres
- 2-3 frases apenas
- Destaque os tópicos principais discutidos
- Mencione conclusões ou decisões importantes
- Se houver próximos passos mencionados, inclua-os
- Use linguagem clara e objetiva
- Não use markdown ou formatação especial

CONVERSA:
{conversation_text}

RESUMO:
"""

    try:
        response = client.messages.create(
            model="MiniMax-M2",
            max_tokens=300,
            system="Você é um assistente especializado em criar resumos concisos e úteis de conversas. Responda SEMPRE em português do Brasil.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        summary = response.content[0].text.strip()

        # Garantir que não excede o limite
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."

        return summary

    except Exception as e:
        print(f"❌ Erro ao gerar resumo: {e}")
        return f"Erro ao gerar resumo: {str(e)}"

async def generate_conversation_summary_stream(messages: list, max_length: int = 500):
    """
    Gera resumo de uma conversa usando LLM com streaming.

    Args:
        messages: Lista de mensagens no formato [{'role': 'user'|'assistant', 'content': '...'}]
        max_length: Comprimento máximo do resumo (padrão: 500 caracteres)

    Yields:
        Chunks de texto do resumo conforme gerado
    """
    if not messages:
        yield "Conversa vazia."
        return

    # Extrair texto das mensagens
    conversation_text = ""
    for msg in messages:
        role = msg.get('role', '').lower()
        content = msg.get('content', '').strip()
        if content:
            prefix = "Usuário" if role == 'user' else "Assistente"
            conversation_text += f"{prefix}: {content}\n\n"

    if not conversation_text.strip():
        yield "Conversa sem conteúdo textual."
        return

    # Truncar se muito longo (limitar a ~3000 caracteres para o prompt)
    if len(conversation_text) > 3000:
        conversation_text = conversation_text[:3000] + "\n\n[... conversação truncada ...]"

    prompt = f"""
Por favor, crie um resumo conciso desta conversa em português brasileiro.

DIRETRIZES:
- Máximo de {max_length} caracteres
- 2-3 frases apenas
- Destaque os tópicos principais discutidos
- Mencione conclusões ou decisões importantes
- Se houver próximos passos mencionados, inclua-os
- Use linguagem clara e objetiva
- Não use markdown ou formatação especial

CONVERSA:
{conversation_text}

RESUMO:
"""

    try:
        # Usar streaming similar ao generate_answer_stream
        with client.messages.stream(
            model="MiniMax-M2",
            max_tokens=300,
            system="Você é um assistente especializado em criar resumos concisos e úteis de conversas. Responda SEMPRE em português do Brasil.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        ) as stream:
            full_text = ""
            # Usar text_stream para evitar ThinkingBlock e outros tipos de chunk
            for text in stream.text_stream:
                full_text += text
                yield text

        # Garantir que não excede o limite
        if len(full_text) > max_length:
            yield "... (resumo truncado)"

    except Exception as e:
        print(f"❌ Erro ao gerar resumo stream: {e}")
        yield f"Erro ao gerar resumo: {str(e)}"
