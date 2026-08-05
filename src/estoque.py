"""
Regras de negócio do estoque:
compara a quantidade disponível com o estoque mínimo e aponta o que precisa de reposição.
"""


def verificar_reposicao(produtos):
    """
    Recebe uma lista de produtos (dicts com quantidade_estoque e estoque_minimo)
    e retorna apenas os que estão no ou abaixo do estoque mínimo.
    """
    produtos_para_repor = []
    for produto in produtos:
        if produto["quantidade_estoque"] <= produto["estoque_minimo"]:
            faltante = max(produto["estoque_minimo"] - produto["quantidade_estoque"], 0)
            produtos_para_repor.append({
                **produto,
                "quantidade_faltante": faltante,
            })
    return produtos_para_repor


def produto_tem_estoque_suficiente(produto, quantidade_pedida):
    """Verifica se um produto tem estoque suficiente para atender a quantidade de um pedido."""
    return produto["quantidade_estoque"] >= quantidade_pedida
