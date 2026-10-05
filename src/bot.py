"""Ponto de entrada da conversa do bot.

Por padrão, tenta responder com a IA (ia.responder -- conversa natural,
sem menu numerado). Se a IA não estiver configurada ou a chamada falhar por
qualquer motivo (sem internet, sem créditos, chave inválida, etc.), cai de
volta no menu fixo numerado original, para o atendimento nunca parar de
funcionar.

Também aplica um limite simples de taxa por telefone: mensagens do MESMO
número chegando mais rápido que RATE_LIMIT_SEGUNDOS não disparam uma nova
chamada de IA (que tem custo, seja em dinheiro no caso do Claude, seja em
CPU/memória no caso do Ollama) -- usam o menu fixo nesse meio tempo. Isso
protege contra flood (de propósito ou por um webhook retransmitindo em
loop) sem bloquear o cliente de verdade.
"""
import logging
import random
import re
import time
import unicodedata

from . import cardapio, config, ia
from .links import gerar_link_pedido

logger = logging.getLogger(__name__)

MENU_TEXTO = (
    "Seja bem-vindo ao nosso autoatendimento 🤖 no que posso ajudar?\n\n"
    "Aqui vão algumas coisas em que eu consigo te ajudar! Digite o número para "
    "iniciar o atendimento:\n"
    "1 - Horário de funcionamento ⏰\n"
    "2 - Realizar pedidos 📝\n"
    "3 - Formas de pagamento 💵\n"
    "4 - Cardápio 🍔\n"
    "5 - Telefone ☎️\n"
    "6 - Promoções 💰\n"
    "7 - Taxa de entrega 🛵\n"
    "8 - Endereço 📍"
)

_ultima_chamada_ia: dict[str, float] = {}


def _dentro_do_rate_limit(telefone: str) -> bool:
    """True se o telefone já chamou a IA há menos de RATE_LIMIT_SEGUNDOS."""
    if config.RATE_LIMIT_SEGUNDOS <= 0:
        return False
    agora = time.monotonic()
    ultima = _ultima_chamada_ia.get(telefone)
    if ultima is not None and (agora - ultima) < config.RATE_LIMIT_SEGUNDOS:
        return True
    _ultima_chamada_ia[telefone] = agora
    return False


def _resposta_opcao(opcao: str, telefone: str) -> str | None:
    if opcao == "1":
        return f"⏰ Nosso horário de funcionamento:\n{config.HORARIO_FUNCIONAMENTO}"
    if opcao == "2":
        link = gerar_link_pedido(telefone)
        return f"Faça o seu pedido em {link}"
    if opcao == "3":
        return (
            "💵 Formas de pagamento aceitas:\n"
            "• Dinheiro\n• Pix\n• Cartão de crédito/débito\n• Vale-alimentação (Cabal, VR, Alelo)"
        )
    if opcao == "4":
        return cardapio.texto_cardapio()
    if opcao == "5":
        return f"☎️ Telefone: {config.TELEFONE_RESTAURANTE}"
    if opcao == "6":
        return "💰 Fique de olho por aqui! Assim que tivermos promoções ativas, avisamos você."
    if opcao == "7":
        return f"🛵 Taxa de entrega: R$ {config.TAXA_ENTREGA:.2f} (grátis na retirada no balcão)"
    if opcao == "8":
        return f"📍 Endereço: {config.ENDERECO_RESTAURANTE}"
    return None


def _normalizar(texto: str) -> str:
    """minúsculo, sem acento e sem pontuação: 'Cardápio?' -> 'cardapio'."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def _tem(texto: str, *termos: str) -> bool:
    """True se algum termo aparece como palavra/expressão inteira."""
    return any(re.search(rf"\b{re.escape(t)}\b", texto) for t in termos)


_SAUDACOES = (
    "Oi! Tudo bem? 😊 Aqui é do {nome}. Como posso te ajudar?",
    "Olá! Seja bem-vindo ao {nome}. Em que posso ajudar?",
    "Opa, tudo certo? Aqui é do {nome}. O que você gostaria hoje?",
)

_NAO_ENTENDI = (
    "Hmm, não entendi direito 😅 Posso te ajudar com cardápio, pedido, "
    "horário, entrega, pagamento ou endereço. É só me dizer o que precisa!"
)


def _processar_mensagem_sem_ia(telefone: str, texto_limpo: str) -> str:
    """Reserva SEM IA (custo zero): entende frases soltas por palavras-chave,
    em vez de despejar um menu numerado. O número do menu antigo (1 a 8)
    continua funcionando."""
    resposta_opcao = _resposta_opcao(texto_limpo, telefone)
    if resposta_opcao is not None:
        return resposta_opcao

    t = _normalizar(texto_limpo)
    if not t:
        return random.choice(_SAUDACOES).format(nome=config.NOME_RESTAURANTE)

    # Intenção de pedir (frases específicas primeiro, pois "entrega" sozinha é ambígua)
    if _tem(t, "fazer pedido", "fazer um pedido", "fazer o pedido", "quero pedir",
            "queria pedir", "quero fazer", "queria fazer", "gostaria de pedir",
            "gostaria de fazer", "pedir", "pedido", "quero um", "quero uma",
            "queria um", "queria uma", "quero comprar"):
        return _resposta_opcao("2", telefone)
    if _tem(t, "taxa", "frete", "quanto e a entrega", "valor da entrega",
            "entregam", "entrega", "delivery"):
        return _resposta_opcao("7", telefone)
    if _tem(t, "cardapio", "menu", "o que tem", "opcoes", "lanches", "lanche", "hamburguer", "preco", "precos", "quanto custa", "valores"):
        return _resposta_opcao("4", telefone)
    if _tem(t, "horario", "horarios", "abre", "abrem", "fecha", "fecham", "aberto",
            "funcionamento", "funciona", "abertos"):
        return _resposta_opcao("1", telefone)
    if _tem(t, "pagamento", "pagar", "pix", "cartao", "dinheiro", "credito", "debito",
            "aceita", "aceitam", "vale", "troco"):
        return _resposta_opcao("3", telefone)
    if _tem(t, "endereco", "onde fica", "onde voces ficam", "localizacao", "como chegar", "onde e"):
        return _resposta_opcao("8", telefone)
    if _tem(t, "telefone", "ligar", "contato", "numero"):
        return _resposta_opcao("5", telefone)
    if _tem(t, "promocao", "promocoes", "promo", "desconto", "oferta", "ofertas", "combo"):
        return _resposta_opcao("6", telefone)
    if _tem(t, "obrigado", "obrigada", "valeu", "brigado", "brigada", "agradeco"):
        return "Por nada! 😊 Qualquer coisa é só chamar."
    if _tem(t, "tchau", "ate mais", "ate logo", "flw", "falou"):
        return "Até mais! Volte sempre 👋"

    saudacao = _tem(t, "oi", "ola", "opa", "eai", "e ai", "oie", "hey", "hello",
                    "bom dia", "boa tarde", "boa noite", "tudo bem", "td bem", "blz", "salve")
    if saudacao:
        return random.choice(_SAUDACOES).format(nome=config.NOME_RESTAURANTE)

    return _NAO_ENTENDI


# Nome antigo mantido para compatibilidade
_processar_mensagem_menu_fixo = _processar_mensagem_sem_ia


def processar_mensagem(telefone: str, texto: str) -> str:
    """Recebe o texto do cliente e devolve a resposta do bot."""
    texto_limpo = (texto or "").strip()

    if _dentro_do_rate_limit(telefone):
        logger.info("Rate limit: %s mandou mensagem rápido demais, usando respostas sem IA", telefone)
        return _processar_mensagem_sem_ia(telefone, texto_limpo)

    try:
        return ia.responder(telefone, texto_limpo)
    except ia.IAIndisponivel as exc:
        logger.warning("IA indisponível, usando respostas sem IA: %s", exc)

    return _processar_mensagem_sem_ia(telefone, texto_limpo)
