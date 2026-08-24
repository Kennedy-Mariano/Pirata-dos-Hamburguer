"""
Gerenciamento de pedidos single-use e geração de recibo (texto).
"""

import uuid
import datetime
import json
from src import db, config


def _generate_token():
    return uuid.uuid4().hex


def create_single_use_token(conn, pedido_id: int, ttl_minutes: int = None) -> str:
    """
    Cria um token único ligado ao pedido_id. Retorna o token.
    Usa a mesma conexão do db.get_connection() passada pelo chamador.
    """
    if ttl_minutes is None:
        ttl_minutes = config.SINGLE_USE_TOKEN_TTL_MINUTES

    token = _generate_token()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=int(ttl_minutes))

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO single_use_tokens (token, pedido_id, used, created_at, expires_at)
            VALUES (%s, %s, false, now(), %s);
        """, (token, pedido_id, expires_at))
        conn.commit()
    return token


def redeem_token(conn, token: str):
    """
    Marca token como usado e retorna pedido_id. Lança ValueError em caso de inválido/expirado/usado.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT token, pedido_id, used, expires_at FROM single_use_tokens WHERE token = %s;", (token,))
        row = cur.fetchone()
        if not row:
            raise ValueError("token_invalido")
        token_db, pedido_id, used, expires_at = row
        if used:
            raise ValueError("token_ja_utilizado")
        if expires_at is not None and expires_at < datetime.datetime.utcnow():
            raise ValueError("token_expirado")

        # marca como usado
        cur.execute("UPDATE single_use_tokens SET used = true WHERE token = %s;", (token,))
        conn.commit()
        return pedido_id


def generate_receipt_text(conn, pedido_id: int) -> str:
    """
    Gera recibo de texto monoespaçado lendo os dados do pedido e itens.
    Retorna string com o recibo.
    """
    with conn.cursor() as cur:
        # busca dados do pedido
        cur.execute("""
            SELECT p.id, p.cliente_nome, p.cliente_telefone, p.created_at
            FROM pedidos p WHERE p.id = %s;
        """, (pedido_id,))
        pedido = cur.fetchone()
        if not pedido:
            raise ValueError("pedido_nao_encontrado")

        cliente_nome = pedido[1] or "Cliente"
        cliente_telefone = pedido[2] or ""
        created_at = pedido[3]

        # busca itens do pedido (join para ter nome e preço)
        cur.execute("""
            SELECT ip.quantidade, ip.preco_unitario, pr.nome
            FROM itens_pedido ip
            JOIN produtos pr ON pr.id = ip.produto_id
            WHERE ip.pedido_id = %s;
        """, (pedido_id,))
        itens = cur.fetchall()

    def format_money(v):
        # usa formato brasileiro 12,34
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    header = "****  DOCUMENTO NAO FISCAL  ****\n\n"
    header += f"{'BARBAROS LANCHES'.center(40)}\n\n"
    s = header
    s += f"N. Pedido:  #{pedido_id}\n"
    s += f"Origem:    Bot Atendimento\n"
    s += f"Data/Hora: {created_at.strftime('%d/%m/%Y - %H:%M:%S') if created_at else ''}\n"
    s += "-"*40 + "\n\n"
    s += f"Cliente:  {cliente_nome}\n"
    s += f"Fone:     {cliente_telefone}\n"
    s += "-"*40 + "\n"
    s += f"F. ENTREGA: RETIRADA BALCAO\n"
    s += "-"*40 + "\n\n"
    s += f"Qtd  Descricao{'' :15} V.Uni  V.Total\n"
    s += "-"*40 + "\n"

    total_pedido = 0.0
    for quantidade, preco_unitario, nome in itens:
        total = quantidade * preco_unitario
        total_pedido += total
        nome_short = (nome[:20]).ljust(20)
        s += f"{int(quantidade):<4} {nome_short} {format_money(preco_unitario):>6}  {format_money(total):>6}\n"

    s += "-"*40 + "\n\n"
    s += f"Total Itens: {format_money(total_pedido)}\n"
    s += f"TOTAL PEDIDO: {format_money(total_pedido)}\n\n"
    s += "TOTAL PAGO:  0,00\n"
    s += f"TOTAL A PAGAR: {format_money(total_pedido)}\n"
    s += "TROCO: 0,00\n\n"
    s += "F. PAGAMENTO: a definir (confirmação no chat)\n"
    s += "-"*40 + "\n\n"
    s += "Obrigado pelo pedido!\n"
    return s
