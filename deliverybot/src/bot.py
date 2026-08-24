"""Máquina de estados simples da conversa do bot — reproduz o menu numerado
dos prints anexados (1 a 8) e a geração do link único de pedido na opção 2.
"""
from . import cardapio, config
from .db import get_conn
from .links import gerar_link_pedido

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

_SAUDACOES = {"oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "opa", "menu", "oii"}


def _obter_estado(telefone: str) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT estado FROM sessoes_bot WHERE telefone = ?", (telefone,)).fetchone()
    return row["estado"] if row else "MENU"


def _definir_estado(telefone: str, estado: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessoes_bot (telefone, estado, atualizado_em) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(telefone) DO UPDATE SET estado = excluded.estado, atualizado_em = datetime('now')",
            (telefone, estado),
        )


def _resposta_opcao(opcao: str, telefone: str) -> str:
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


def processar_mensagem(telefone: str, texto: str) -> str:
    """Recebe o texto do cliente e devolve a resposta do bot."""
    texto_limpo = (texto or "").strip()
    opcao = texto_limpo.strip()

    resposta_opcao = _resposta_opcao(opcao, telefone)
    if resposta_opcao is not None:
        _definir_estado(telefone, "MENU")
        return resposta_opcao

    # Qualquer outra mensagem (saudação, ou texto que não bate com o menu) volta pro menu.
    return MENU_TEXTO
