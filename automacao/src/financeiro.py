"""
Cálculo do custo efetivo, receita e lucro de cada pedido/período.
"""
from decimal import Decimal


def calcular_item(quantidade, preco_unitario, custo_unitario):
    """Retorna receita, custo e lucro de UM item do pedido."""
    quantidade = Decimal(quantidade)
    preco_unitario = Decimal(str(preco_unitario))
    custo_unitario = Decimal(str(custo_unitario))

    receita = quantidade * preco_unitario
    custo = quantidade * custo_unitario
    lucro = receita - custo
    return {
        "receita": float(receita),
        "custo": float(custo),
        "lucro": float(lucro),
    }


def calcular_resumo_pedido(itens):
    """
    itens = [{"quantidade": 2, "preco_unitario": 45.0, "custo_unitario": 18.0}, ...]
    Retorna o total de receita, custo e lucro do pedido inteiro.
    """
    total_receita = total_custo = total_lucro = 0.0
    for item in itens:
        valores = calcular_item(item["quantidade"], item["preco_unitario"], item["custo_unitario"])
        total_receita += valores["receita"]
        total_custo += valores["custo"]
        total_lucro += valores["lucro"]

    return {
        "receita_total": round(total_receita, 2),
        "custo_total": round(total_custo, 2),
        "lucro_total": round(total_lucro, 2),
        "margem_percentual": round((total_lucro / total_receita) * 100, 2) if total_receita else 0.0,
    }


def calcular_resumo_periodo(linhas_powerbi):
    """
    Agrega o resultado de várias linhas (vindas da view vw_powerbi_pedidos) em um
    resumo geral: receita, custo e lucro do período todo.
    """
    receita = sum(float(l["receita"]) for l in linhas_powerbi)
    custo = sum(float(l["custo_total"]) for l in linhas_powerbi)
    lucro = sum(float(l["lucro"]) for l in linhas_powerbi)
    return {
        "receita_total": round(receita, 2),
        "custo_total": round(custo, 2),
        "lucro_total": round(lucro, 2),
        "margem_percentual": round((lucro / receita) * 100, 2) if receita else 0.0,
        "quantidade_pedidos": len({l["pedido_id"] for l in linhas_powerbi}),
    }
