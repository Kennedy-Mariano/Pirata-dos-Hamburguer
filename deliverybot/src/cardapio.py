from .db import get_conn


def listar_produtos_ativos():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nome, categoria, descricao, preco FROM produtos WHERE ativo = 1 ORDER BY categoria, nome"
        ).fetchall()
    return [dict(r) for r in rows]


def agrupar_por_categoria(produtos):
    grupos = {}
    for p in produtos:
        grupos.setdefault(p["categoria"], []).append(p)
    return grupos


def buscar_produto(produto_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, nome, categoria, descricao, preco FROM produtos WHERE id = ? AND ativo = 1",
            (produto_id,),
        ).fetchone()
    return dict(row) if row else None


def texto_cardapio() -> str:
    """Monta o texto do cardápio para responder à opção 4 do menu do bot."""
    produtos = listar_produtos_ativos()
    grupos = agrupar_por_categoria(produtos)
    linhas = ["📋 *Nosso cardápio:*", ""]
    for categoria, itens in grupos.items():
        linhas.append(f"*{categoria}*")
        for item in itens:
            linhas.append(f"• {item['nome']} — R$ {item['preco']:.2f}")
        linhas.append("")
    return "\n".join(linhas).strip()
