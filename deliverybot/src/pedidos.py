import random

from . import config
from .db import get_conn


def gerar_numero_pedido() -> str:
    """Gera um número de pedido de 8 dígitos, no estilo '#21535858' dos prints."""
    return "#" + "".join(str(random.randint(0, 9)) for _ in range(8))


def obter_ou_criar_cliente(telefone: str, nome: str, cep: str = "", endereco: str = "") -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM clientes WHERE telefone = ?", (telefone,)).fetchone()
        if row:
            conn.execute(
                "UPDATE clientes SET nome = ?, cep = COALESCE(NULLIF(?, ''), cep), "
                "endereco = COALESCE(NULLIF(?, ''), endereco) WHERE id = ?",
                (nome, cep, endereco, row["id"]),
            )
            return row["id"]

        cur = conn.execute(
            "INSERT INTO clientes (nome, telefone, cep, endereco) VALUES (?, ?, ?, ?)",
            (nome, telefone, cep, endereco),
        )
        return cur.lastrowid


def criar_pedido(
    telefone: str,
    nome_cliente: str,
    itens: list[dict],
    forma_pagamento: str,
    forma_entrega: str = "RETIRADA BALCAO",
    cep: str = "",
    endereco: str = "",
) -> dict:
    """itens: lista de {'produto_id': int, 'quantidade': int}. Retorna o pedido criado com os itens."""
    if not itens:
        raise ValueError("O pedido precisa ter pelo menos um item.")

    cliente_id = obter_ou_criar_cliente(telefone, nome_cliente, cep, endereco)

    with get_conn() as conn:
        total_itens = 0.0
        itens_resolvidos = []
        for item in itens:
            produto = conn.execute(
                "SELECT * FROM produtos WHERE id = ? AND ativo = 1", (item["produto_id"],)
            ).fetchone()
            if produto is None:
                continue
            quantidade = max(1, int(item.get("quantidade", 1)))
            subtotal = produto["preco"] * quantidade
            total_itens += subtotal
            itens_resolvidos.append(
                {
                    "produto_id": produto["id"],
                    "nome": produto["nome"],
                    "quantidade": quantidade,
                    "preco_unitario": produto["preco"],
                    "subtotal": subtotal,
                }
            )

        if not itens_resolvidos:
            raise ValueError("Nenhum item válido foi encontrado no pedido.")

        taxa_entrega = config.TAXA_ENTREGA if forma_entrega == "ENTREGA" else 0.0
        total_pedido = total_itens + taxa_entrega

        numero_pedido = gerar_numero_pedido()
        while conn.execute(
            "SELECT 1 FROM pedidos WHERE numero_pedido = ?", (numero_pedido,)
        ).fetchone():
            numero_pedido = gerar_numero_pedido()

        cur = conn.execute(
            "INSERT INTO pedidos (numero_pedido, cliente_id, forma_entrega, tempo_estimado_min, "
            "forma_pagamento, total_itens, total_pedido, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'RECEBIDO')",
            (
                numero_pedido,
                cliente_id,
                forma_entrega,
                config.TEMPO_PREPARO_MIN,
                forma_pagamento,
                round(total_itens, 2),
                round(total_pedido, 2),
            ),
        )
        pedido_id = cur.lastrowid

        for item in itens_resolvidos:
            conn.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
                "VALUES (?, ?, ?, ?)",
                (pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"]),
            )

        posicao = conn.execute(
            "SELECT COALESCE(MAX(posicao), 0) + 1 AS pos FROM fila_preparo"
        ).fetchone()["pos"]
        conn.execute(
            "INSERT INTO fila_preparo (pedido_id, posicao, status) VALUES (?, ?, 'AGUARDANDO')",
            (pedido_id, posicao),
        )

    return obter_pedido(pedido_id)


def obter_pedido(pedido_id: int) -> dict | None:
    with get_conn() as conn:
        pedido = conn.execute(
            "SELECT p.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone, "
            "c.cep AS cliente_cep, c.endereco AS cliente_endereco "
            "FROM pedidos p JOIN clientes c ON c.id = p.cliente_id WHERE p.id = ?",
            (pedido_id,),
        ).fetchone()
        if pedido is None:
            return None
        itens = conn.execute(
            "SELECT ip.*, pr.nome AS produto_nome FROM itens_pedido ip "
            "JOIN produtos pr ON pr.id = ip.produto_id WHERE ip.pedido_id = ?",
            (pedido_id,),
        ).fetchall()

    pedido = dict(pedido)
    pedido["itens"] = [dict(i) for i in itens]
    return pedido


def obter_pedido_por_numero(numero_pedido: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM pedidos WHERE numero_pedido = ?", (numero_pedido,)
        ).fetchone()
    return obter_pedido(row["id"]) if row else None


def registrar_mensagem(telefone: str, direcao: str, conteudo: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO mensagens (telefone, direcao, conteudo) VALUES (?, ?, ?)",
            (telefone, direcao, conteudo),
        )
