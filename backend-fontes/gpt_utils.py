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
    "Desculpe, ainda não tenho informações suficientes sobre esse tema específico do curso. "
    "Por favor, envie outra pergunta ou consulte o material da aula."
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
    "Olá, Doutor(a), seja muito bem-vindo(a)!",
    "Oi, Doutor(a), tudo bem? Como posso ajudar?",
    "Bem-vindo(a) de volta, Doutor(a)! Pronto(a) para evoluir seu consultório?",
    "Olá, Doutor(a)! Estou aqui para apoiar você no seu crescimento."
]

CLOSINGS = [
    "Ficou com alguma dúvida sobre esta aula, Doutor(a)?",
    "Deseja aprofundar algum ponto, seguir para a próxima aula, voltar, repetir ou escolher outro módulo?",
    "Se quiser, escolha uma opção rápida abaixo ou pergunte de novo!",
    "Se quiser ir para outra aula, módulo ou tema, é só pedir, Doutor(a).",
    "Essa resposta foi útil? Clique em 👍 ou 👎."
]

AULAS_POR_MODULO = {
    1: ['1.1', '1.2', '1.3', '1.4', '1.5'],
    2: ['2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8', '2.9'],
    3: ['3.1', '3.2', '3.3', '3.4', '3.5'],
    4: ['4.1', '4.2', '4.3', '4.4', '4.5'],
    5: ['5.1', '5.2', '5.3', '5.4', '5.5'],
    6: ['6.1', '6.2', '6.3', '6.4', '6.5'],
    7: ['7.1', '7.2', '7.3', '7.4', '7.5', '7.6', '7.7', '7.8', '7.9'],
}

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
    opcoes = ["Aprofundar esta aula", "Próxima aula", "Tenho outra dúvida"]
    if progresso:
        modulo = progresso.get('modulo', 1)
        opcoes.append("Voltar para aula anterior")
        opcoes.append("Repetir esta aula")
        opcoes.append("Escolher módulo ou aula específica")
        if modulo < 7:
            opcoes.append("Ir para o próximo módulo")
        if modulo > 1:
            opcoes.append("Ir para o módulo anterior")
    if isinstance(explicacao, str) and "Quer que eu continue?" in explicacao:
        # Ajuda o usuário a pedir continuação explicitamente
        opcoes.insert(0, "Continuar")
    return opcoes

def resposta_link(titulo, url, icone="📄"):
    return f"<br><a class='chip' href='{url}' target='_blank'>{icone} {titulo}</a>"

def resposta_link_externo(titulo, url, icone="🔗"):
    return f"<br><a class='chip' href='{url}' target='_blank'>{icone} {titulo}</a>"

# >>>>> MELHORIA APENAS NA DETECÇÃO DE CENÁRIOS DE DÚVIDAS PRÁTICAS <<<<<
def detectar_cenario(pergunta: str) -> str:
    pergunta = pergunta.lower()
    
    # Especialidades médicas reconhecidas para o método
    especialidades = [
        "dermatologista", "psicóloga", "psicologo", "pediatra", "dentista",
        "fonoaudióloga", "fonoaudiologo", "nutricionista", "veterinário", "veterinaria",
        "psicanalista", "fisioterapeuta", "terapeuta", "acupunturista"
    ]
    # Termos que sugerem intenção de atrair, crescer, captar, faturar etc
    termos_acao = [
        "atrair", "captar", "faturar", "paciente high ticket", "crescer", "aplicar",
        "ter mais pacientes", "dobrar faturamento", "ganhar mais", "aumentar", "consultório cheio",
        "lotar agenda", "consultorio", "atendimento particular"
    ]

    # Se mencionar especialidade + intenção prática, é dúvida pontual
    if any(f"sou {esp}" in pergunta for esp in especialidades) and any(
        t in pergunta for t in termos_acao
    ):
        return "duvida_pontual"
    # Detecta perguntas tipo "como faço para", "como atrair", "quero aumentar"
    if re.search(r"como\s+faço|como\s+atrair|quero\s+(aumentar|dobrar|captar|faturar|ter mais|consultório|consultorio|lotar)", pergunta):
        return "duvida_pontual"
    # Detecta dúvidas sobre módulos, aulas, navegação (MANTÉM O FLUXO DE MÓDULOS)
    if any(p in pergunta for p in [
        "quero fazer o curso completo", "começar do início", "me ensina tudo",
        "fazer o curso com você", "menu", "ver módulos", "ver o curso", "ver estrutura", "iniciar o curso", "quero começar o curso"
    ]):
        return "curso_completo"
    elif re.search(r'\bm[oó]dulo\s*\d+\b', pergunta) or re.search(r'\baula\s*\d+\.\d+\b', pergunta):
        return "navegacao_especifica"
    elif any(p in pergunta for p in ["voltar", "retornar", "anterior", "repetir aula"]):
        return "voltar"
    elif any(p in pergunta for p in [
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
# <<<<< FIM DA MELHORIA APENAS NA DETECÇÃO DE CENÁRIOS DE DÚVIDAS PRÁTICAS >>>>>

def encontrar_modulo_aula(pergunta):
    pergunta = pergunta.lower()
    m_modulo = re.search(r'\bm[oó]dulo\s*(\d+)\b', pergunta)
    m_aula = re.search(r'\baula\s*(\d+\.\d+)\b', pergunta)
    modulo = None
    aula = None
    if m_modulo:
        modulo = int(m_modulo.group(1))
    if m_aula:
        aula = m_aula.group(1)
    return modulo, aula

def atualizar_progresso(pergunta: str, progresso: dict) -> dict:
    # Sempre começa pelo módulo 1
    if not progresso:
        return {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': True}

    pergunta_lower = pergunta.strip().lower()
    modulo_nav, aula_nav = encontrar_modulo_aula(pergunta)
    cenario = detectar_cenario(pergunta)

    # Começar do início
    if cenario == "curso_completo":
        return {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': False}

    if modulo_nav is not None and modulo_nav in AULAS_POR_MODULO:
        progresso['modulo'] = modulo_nav
        if aula_nav and aula_nav in AULAS_POR_MODULO.get(modulo_nav, []):
            progresso['aula'] = aula_nav
        else:
            progresso['aula'] = AULAS_POR_MODULO[modulo_nav][0]
        progresso['etapa'] = 1
        progresso['visao_geral'] = False
        progresso['aguardando_duvida'] = False
        return progresso
    elif aula_nav:
        for m, aulas in AULAS_POR_MODULO.items():
            if aula_nav in aulas:
                progresso['modulo'] = m
                progresso['aula'] = aula_nav
                progresso['etapa'] = 1
                progresso['visao_geral'] = False
                progresso['aguardando_duvida'] = False
                return progresso

    # Voltar aula ou módulo
    if any(p in pergunta_lower for p in ["voltar", "retornar", "anterior"]):
        modulo = progresso['modulo']
        aula_atual = progresso['aula']
        aulas = AULAS_POR_MODULO.get(modulo, [])
        idx = aulas.index(aula_atual) if aula_atual in aulas else 0
        if idx > 0:
            progresso['aula'] = aulas[idx-1]
            progresso['etapa'] = 1
        else:
            if modulo > 1:
                progresso['modulo'] = modulo - 1
                progresso['aula'] = AULAS_POR_MODULO[modulo-1][-1]
                progresso['etapa'] = 1
        progresso['visao_geral'] = False
        progresso['aguardando_duvida'] = False
        return progresso

    # Repetir aula
    if "repetir" in pergunta_lower:
        progresso['etapa'] = 1
        progresso['aguardando_duvida'] = False
        progresso['visao_geral'] = False
        return progresso

    # Avançar aula
    if any(p in pergunta_lower for p in ["próxima aula", "avançar", "continuar", "pode avançar"]):
        modulo = progresso['modulo']
        aula_atual = progresso['aula']
        aulas = AULAS_POR_MODULO.get(modulo, [])
        idx = aulas.index(aula_atual) if aula_atual in aulas else 0
        if idx < len(aulas)-1:
            progresso['aula'] = aulas[idx+1]
            progresso['etapa'] = 1
        else:
            if modulo < 7:
                progresso['modulo'] = modulo + 1
                progresso['aula'] = AULAS_POR_MODULO[modulo+1][0]
                progresso['etapa'] = 1
        progresso['visao_geral'] = False
        progresso['aguardando_duvida'] = False
        return progresso

    # "Sim" deve AVANÇAR ETAPA ou IR PRA AULA
    if pergunta_lower in ["sim", "sim desejo", "quero sim", "vamos", "ok"]:
        if progresso.get('visao_geral', True):
            progresso['visao_geral'] = False
            progresso['modulo'] = 1
            progresso['aula'] = '1.1'
            progresso['etapa'] = 1
        elif progresso.get('etapa', 1) < 3:
            progresso['etapa'] += 1
        else:
            progresso['aguardando_duvida'] = True
    # "Não" avança para próxima aula ou módulo
    elif pergunta_lower in ["não", "nao", "não tenho dúvida", "nao tenho duvida"]:
        if progresso.get('aguardando_duvida'):
            progresso['aguardando_duvida'] = False
            modulo = progresso['modulo']
            aula_atual = progresso['aula']
            aulas = AULAS_POR_MODULO.get(modulo, [])
            idx = aulas.index(aula_atual) if aula_atual in aulas else 0
            if idx < len(aulas)-1:
                progresso['aula'] = aulas[idx+1]
            else:
                if modulo < 7:
                    progresso['modulo'] = modulo + 1
                    progresso['aula'] = AULAS_POR_MODULO[modulo+1][0]
            progresso['etapa'] = 1
            progresso['visao_geral'] = False
    return progresso

# BLOCO DE MÓDULOS E AULAS – COMEÇA NO MÓDULO 01
BLOCO_MODULOS = """
módulo 01 – mentalidade high ticket: como desenvolver uma mente preparada para atrair pacientes high ticket
1.1. introdução – a mentalidade do especialista high ticket: o primeiro passo para dobrar o faturamento do consultório
1.2. como quebrar bloqueios com dinheiro e valorizar seu trabalho no consultório high ticket
1.3. como desenvolver autoconfiança profissional e se tornar autoridade no consultório high ticket
1.4. concorrência: como se diferenciar e construir valorização profissional
1.5. boas práticas no atendimento: o caminho mais rápido para o consultório high ticket

módulo 02 – senso estético high ticket: como transformar sua imagem e ambiente para atrair pacientes que valorizam
2.1. o senso estético high ticket
2.2. mulheres: senso estético high ticket x cafona
2.3. homens no consultório high ticket: senso estético, imagem e escolhas que atraem ou afastam pacientes
2.4. senso estético high ticket na decoração: o que priorizar e o que evitar no consultório
2.5. papelaria e brindes
2.6. como fazer o paciente se sentir especial e gerar mais valor na percepção dele
2.7. checklist: o que você precisa mudar hoje no seu consultório para dobrar o faturamento com o senso estético
2.8. como tornar a primeira impressão do paciente inesquecível
2.9. o que é cafona no consultório e afasta paciente high ticket

módulo 03 – posicionamento presencial high ticket: como construir autoridade sem redes sociais
3.1. posicionamento presencial high ticket: estratégias para construir autoridade e valor no consultório
3.2. você é um cnpj: riscos, proteção jurídica e postura profissional no consultório high ticket
3.3. como causar uma boa primeira impressão no consultório high ticket
3.4. como causar uma boa impressão pessoal no consultório high ticket: educação, pontualidade e respeito
3.5. posicionamento em eventos sociais e exposição na mídia: comportamento e limites para fortalecer sua autoridade e atrair pacientes high ticket

módulo 04 – a jornada do paciente high ticket: como transformar atendimento em encantamento e fidelização
4.1. a jornada do paciente high ticket: conceito e regras de ouro para o consultório
4.2. o que o paciente nunca te falará: detalhes essenciais para encantar pacientes high ticket
4.3. secretária e assistente virtual high ticket: funções, riscos e boas práticas para consultórios lucrativos
4.4. o primeiro contato: como organizar e profissionalizar a marcação de consultas desde o início
4.5. marcação de consulta high ticket: como organizar horários, valor e scripts para reduzir faltas e valorizar seu atendimento

módulo 05 – estratégias de captação e fidelização: como atrair pacientes high ticket sem tráfego ou redes sociais
5.1. passo a passo completo para atrair e reter pacientes high ticket com o método consultório high ticket
5.2. o impacto do lifetime value do paciente high ticket no crescimento do consultório
5.3. como nichar o consultório para atrair pacientes high ticket
5.4. estratégias práticas de networking para atração de pacientes high ticket
5.5. estratégias para atrair pacientes high ticket ao começar do absoluto zero

módulo 06 – estratégias de vendas high ticket: como apresentar e fechar tratamentos de alto valor com ética
6.1. os passos fundamentais para dobrar o faturamento do consultório com vendas high ticket
6.2. como migrar dos convênios para o atendimento particular de forma segura e organizada
6.3. como aumentar o valor da sua consulta de forma estratégica e segura
6.4. como e quando dar descontos para pacientes high ticket: estratégia ética e eficaz
6.5. técnica alanis – como usar apresentação visual para vencer objeções e fechar tratamentos high ticket

módulo 07 – estratégias por especialidade
7.1. saúde das crianças – estratégias para consultórios pediátricos high ticket
7.2. saúde feminina – estratégias high ticket para ginecologia, obstetrícia e saúde da mulher
7.3. saúde do idoso – estratégias high ticket para geriatria e atenção ao idoso
7.4. cirurgiões – como apresentar valor, orçamento e experiência high ticket
7.5. doenças sérias – como conduzir pacientes em situações críticas no consultório high ticket
7.6. profissionais com atendimento misto – estratégias para consultórios com diferentes públicos
7.7. profissionais com baixa rotatividade – estratégias para retorno e fidelização
7.8. profissionais da estética – estratégias para consultórios estéticos e de autocuidado
7.9. nutricionistas – estratégias high ticket para emagrecimento, nutrologia e endocrinologia
"""

def generate_answer(question, context="", history=None, tipo_de_prompt=None, is_first_question=True):
    if history and isinstance(history, list) and len(history) > 0:
        ultimo_item = history[-1]
        progresso = ultimo_item.get('progresso', None)
        if not progresso:
            progresso = {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': True}
    else:
        progresso = {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': True}

    progresso = atualizar_progresso(question, progresso)
    modulo = progresso.get('modulo', 1)
    aula = progresso.get('aula', '1.1')
    etapa = progresso.get('etapa', 1)
    aguardando_duvida = progresso.get('aguardando_duvida', False)
    visao_geral = progresso.get('visao_geral', False)

    saudacao = random.choice(GREETINGS) if is_first_question else ""
    fechamento = random.choice(CLOSINGS)
    cenario = detectar_cenario(question)

    mensagem_generica = question.strip().lower()
    saudacoes_vagas = [
        "olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "pode me ajudar?", "oi, tudo bem?",
        "olá bom dia", "tudo bem?", "tudo certo?", "como vai?", "você pode me ajudar?", "me ajuda?", "olá, boa noite"
    ]
    apresentacoes_vagas = ["meu nome é", "sou ", "me apresentando", "me apresento", "me chamo"]

    # Mensagens vagas ("oi", "tudo bem?") devem ir para a LLM (não resposta mock).
    is_saudacao = (
        mensagem_generica in saudacoes_vagas
        or any(mensagem_generica.startswith(apr) for apr in apresentacoes_vagas)
    )
    if is_saudacao:
        cenario = "saudacao"

    # Dúvida pontual, exemplo, etc.
    if cenario in ["duvida_pontual", "exemplo_pratico", "curso_completo", "navegacao_especifica", "saudacao"] or visao_geral:
        if cenario == "saudacao":
            instruction = (
                "O Doutor(a) enviou uma saudação/mensagem inicial (ex: 'oi', 'tudo bem?'). "
                "Responda de forma acolhedora e objetiva, explique rapidamente como você pode ajudar no curso, "
                "e peça uma informação prática para continuar (módulo/aula atual ou especialidade/objetivo)."
            )
        elif cenario in ["curso_completo", "navegacao_especifica"] or visao_geral:
            instruction = (
                "O Doutor(a) quer orientação de navegação no curso. "
                "Liste os 7 módulos e algumas opções de próximos passos, "
                "SEMPRE citando os títulos exatamente como estão na estrutura fornecida. "
                "No final, peça para o Doutor(a) escolher um módulo/aula (ex: 'módulo 2, aula 2.3') "
                "ou dizer a especialidade para você adaptar."
            )
        else:
            instruction = (
                "Ótima pergunta, Doutor(a)!<br>"
                "Aqui está uma explicação detalhada sobre esse ponto do curso, seguida de um exemplo prático para aplicar no seu consultório, se possível.<br>"
                "Se quiser aprofundar ou pedir mais exemplos clínicos, é só pedir!<br>"
                "Fique à vontade para perguntar qualquer coisa relacionada ao método."
            )
        prompt = f"""{instruction}

{CONTINUE_GUARDRAILS}

Você é a professora Nanda, uma inteligência artificial altamente didática, criada especificamente para ensinar e tirar dúvidas de Doutores(as) que estudam o Curso Online Consultório High Ticket, ministrado por Nanda Mac Dowell.

Leia atentamente o histórico da conversa antes de responder, compreendendo o contexto exato da interação atual para garantir precisão na sua resposta.

IMPORTANTE: Sempre cite o nome do módulo e título da aula exatamente como está na estrutura abaixo. Não adapte, não resuma, não traduza.

ESTRUTURA COMPLETA DO CURSO – MÓDULOS E AULAS:

{BLOCO_MODULOS}

Histórico da conversa anterior:
{formatar_historico_para_prompt(history)}

Pergunta atual do Doutor(a):
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

    # Etapas didáticas
    if etapa in [1, 2, 3] or aguardando_duvida:
        if etapa == 1:
            instruction = (
                f"Você está iniciando a aula {aula} do módulo {modulo}.<br>"
                "O objetivo desta aula é apresentar a você, Doutor(a), conceitos essenciais e estratégias práticas para transformar seu consultório.<br>"
                "Durante o conteúdo, posso trazer exemplos reais, simulações de conversa e até um mini-roteiro prático para facilitar a aplicação.<br><br>"
                "Deseja começar agora mesmo? Responda 'sim' para avançar, ou me pergunte se quiser um exemplo prático logo no início."
            )
        elif etapa == 2:
            instruction = (
                f"Agora vamos tornar o conteúdo da aula {aula} do módulo {modulo} mais prático para a sua realidade clínica.<br>"
                "<b>Exemplo prático de aplicação:</b><br>"
                "- Imagine que você atende um paciente novo e, antes de falar de valores, destaca a importância do vínculo e do acompanhamento contínuo.<br>"
                "Frase que pode usar: 'Meu objetivo é que cada paciente se sinta seguro e confiante, pois assim conseguimos melhores resultados a longo prazo.'<br>"
                "- Se quiser um roteiro de abordagem ou um diálogo simulado, é só pedir!"
            )
        else:
            instruction = (
                f"Você está concluindo a aula {aula} do módulo {modulo}. Recapitule os principais aprendizados de forma sucinta. "
                "Se quiser, posso fechar com um exemplo prático do que foi ensinado, ou aprofundar algum ponto específico.<br>"
                "Pergunte se ficou alguma dúvida, ou se o Doutor(a) quer uma explicação extra, voltar, pular ou escolher outro módulo antes de considerar a aula concluída."
            )
            progresso['aguardando_duvida'] = True

        prompt = f"""{instruction}

{CONTINUE_GUARDRAILS}

Você é a professora Nanda, uma inteligência artificial altamente didática, criada especificamente para ensinar e tirar dúvidas de Doutores(as) que estudam o Curso Online Consultório High Ticket, ministrado por Nanda Mac Dowell.

Leia atentamente o histórico da conversa antes de responder, compreendendo o contexto exato da interação atual para garantir precisão na sua resposta.

IMPORTANTE: Sempre cite o nome do módulo e título da aula exatamente como está na estrutura abaixo. Não adapte, não resuma, não traduza.

ESTRUTURA COMPLETA DO CURSO – MÓDULOS E AULAS:

{BLOCO_MODULOS}

Histórico da conversa anterior:
{formatar_historico_para_prompt(history)}

Pergunta atual do Doutor(a):
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

    # Fallback
    explicacao = OUT_OF_SCOPE_MSG
    quick_replies = gerar_quick_replies(question, explicacao, history, progresso)
    return explicacao, quick_replies, progresso


# ========== FUNÇÃO DE STREAMING PARA WEBSOCKET ==========
async def generate_answer_stream(question, context="", history=None, tipo_de_prompt=None, is_first_question=False):
    """
    Versão streaming da generate_answer para uso com WebSocket.
    Yields dicionários com tipo de conteúdo e dados.

    Yields:
        dict: {"type": "metadata"|"text"|"complete", "data": {...}}
    """
    if history and isinstance(history, list) and len(history) > 0:
        ultimo_item = history[-1]
        progresso = ultimo_item.get('progresso', None)
        if not progresso:
            progresso = {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': True}
    else:
        progresso = {'modulo': 1, 'aula': '1.1', 'etapa': 1, 'aguardando_duvida': False, 'visao_geral': True}

    progresso = atualizar_progresso(question, progresso)
    cenario = detectar_cenario(question)

    saudacao = random.choice(GREETINGS) if is_first_question else ""
    fechamento = random.choice(CLOSINGS)

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
            "O Doutor(a) enviou uma saudação/mensagem inicial (ex: 'oi', 'tudo bem?'). "
            "Responda acolhedor e objetivo, explique rapidamente como pode ajudar no curso, "
            "e peça uma informação prática para continuar (módulo/aula atual ou especialidade/objetivo)."
        )
    elif cenario in ["curso_completo", "navegacao_especifica"]:
        instruction = (
            "O Doutor(a) quer orientação de navegação no curso. "
            "Liste os 7 módulos e algumas opções de próximos passos, "
            "SEMPRE citando os títulos exatamente como estão na estrutura fornecida. "
            "No final, peça para o Doutor(a) escolher um módulo/aula (ex: 'módulo 2, aula 2.3') "
            "ou dizer a especialidade para você adaptar."
        )
    elif cenario in ["duvida_pontual", "exemplo_pratico"]:
        instruction = (
            "Ótima pergunta, Doutor(a)!<br>"
            "Aqui está uma explicação detalhada sobre esse ponto do curso, seguida de um exemplo prático para aplicar no seu consultório, se possível.<br>"
        )
    else:
        instruction = ""

    prompt = f"""{instruction}

{CONTINUE_GUARDRAILS}

Você é a professora Nanda, uma inteligência artificial altamente didática, criada especificamente para ensinar e tirar dúvidas de Doutores(as) que estudam o Curso Online Consultório High Ticket, ministrado por Nanda Mac Dowell.

Leia atentamente o histórico da conversa antes de responder, compreendendo o contexto exato da interação atual para garantir precisão na sua resposta.

IMPORTANTE: Sempre cite o nome do módulo e título da aula exatamente como está na estrutura abaixo. Não adapte, não resuma, não traduza.

ESTRUTURA COMPLETA DO CURSO – MÓDULOS E AULAS:

{BLOCO_MODULOS}

Histórico da conversa anterior:
{formatar_historico_para_prompt(history)}

Pergunta atual do Doutor(a):
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
