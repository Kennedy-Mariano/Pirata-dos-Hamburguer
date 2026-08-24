from .db import get_conn
from . import pedidos as pedidos_repo
from . import recibo
from . import whatsapp

_TRANSICOES = {
    "AGUARDANDO": "EM_PREPARO",
    "EM_PREPARO": "PRONTO",
    "PRONTO": "RETIRADO",
}

_STATUS_FILA_PARA_PEDIDO = {
    "AGUARDANDO": "CONFIRMADO",
    "EM_PREPARO": "EM_PREPARO",
    "PRONTO": "PRONTO",
    "RETIRADO": "RETIRADO",
}


def listar_fila():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT f.*, p.numero_pedido, p.total_pedido, p.forma_entrega, p.forma_pagamento, "
            "c.nome AS cliente_nome, c.telefone AS cliente_telefone "
            "FROM fila_preparo f "
            "JOIN pedidos p ON p.id = f.pedido_id "
            "JOIN clientes c ON c.id = p.cliente_id "
            "WHERE f.status != 'RETIRADO' "
            "ORDER BY f.posicao"
        ).fetchall()
    return [dict(r) for r in rows]


def avancar_status(pedido_id: int) -> dict:
    """Avança o pedido para o próximo status da fila e notifica o cliente no WhatsApp."""
    with get_conn() as conn:
        fila = conn.execute(
            "SELECT * FROM fila_preparo WHERE pedido_id = ?", (pedido_id,)
        ).fetchone()
        if fila is None:
            raise ValueError("Pedido não encontrado na fila de preparo.")

        proximo = _TRANSICOES.get(fila["status"])
        if proximo is None:
            raise ValueError(f"Pedido já está no status final ({fila['status']}).")

        conn.execute(
            "UPDATE fila_preparo SET status = ?, atualizado_em = datetime('now') WHERE pedido_id = ?",
            (proximo, pedido_id),
        )
        conn.execute(
            "UPDATE pedidos SET status = ?, atualizado_em = datetime('now') WHERE id = ?",
            (_STATUS_FILA_PARA_PEDIDO[proximo], pedido_id),
        )

    pedido = pedidos_repo.obter_pedido(pedido_id)
    mensagem = recibo.montar_mensagem_status(pedido, _STATUS_FILA_PARA_PEDIDO[proximo])
    whatsapp.enviar_mensagem(pedido["cliente_telefone"], mensagem)
    pedidos_repo.registrar_mensagem(pedido["cliente_telefone"], "SAIDA", mensagem)
    return pedido
