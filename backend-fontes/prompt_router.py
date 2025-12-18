def inferir_tipo_de_prompt(pergunta: str) -> str:
    pergunta_lower = pergunta.lower()

    # 📩 Mensagens automáticas (WhatsApp, e-mail, direct, etc.)
    termos_mensagem_auto = [
        "mensagem automática", "resposta automática", "mensagem padrão",
        "robô", "responder depois", "responder mais tarde", "sem tempo para responder",
        "fim de semana", "fora do horário", "mensagem fora do expediente"
    ]
    if any(t in pergunta_lower for t in termos_mensagem_auto):
        return "mensagem_automatica"

    # 🔎 Health Plan
    if (
        "health plan" in pergunta_lower
        or "plano de tratamento" in pergunta_lower
        or "meu health plan" in pergunta_lower
        or "fazer meu health plan" in pergunta_lower
        or "fazer meu plano" in pergunta_lower
        or "dúvida no health" in pergunta_lower
        or "dúvida no plano" in pergunta_lower
        or "como montar meu health" in pergunta_lower
        or "como montar meu plano" in pergunta_lower
        or "criar meu plano" in pergunta_lower
        or "montar health plan" in pergunta_lower
        or "montar plano" in pergunta_lower
        or ("sou pediatra" in pergunta_lower and "health" in pergunta_lower)
        or ("sou psicóloga" in pergunta_lower and "ansiedade" in pergunta_lower)
    ):
        return "health_plan"

    # 💰 Precificação
    if (
        "preço" in pergunta_lower
        or "valor" in pergunta_lower
        or "cobrar" in pergunta_lower
        or "precificar" in pergunta_lower
    ):
        return "precificacao"

    # 📣 Captação sem marketing digital
    if (
        "atrair pacientes" in pergunta_lower
        or "sem marketing" in pergunta_lower
        or "sem instagram" in pergunta_lower
    ):
        return "capitacao_sem_marketing_digital"

    # 🔧 Aplicação prática
    if (
        "como aplicar" in pergunta_lower
        or "exemplo prático" in pergunta_lower
        or "na prática" in pergunta_lower
    ):
        return "aplicacao"

    # ❌ Correção de erro
    if (
        "errei" in pergunta_lower
        or "confundi" in pergunta_lower
        or "não entendi" in pergunta_lower
    ):
        return "correcao"

    # 🧠 Revisão rápida
    if (
        "resumo" in pergunta_lower
        or "revisão" in pergunta_lower
    ):
        return "revisao"

    # ❓ Dúvida frequente
    if (
        "muitos perguntam" in pergunta_lower
        or "pergunta comum" in pergunta_lower
    ):
        return "faq"

    # 📘 Explicação padrão
    return "explicacao"
