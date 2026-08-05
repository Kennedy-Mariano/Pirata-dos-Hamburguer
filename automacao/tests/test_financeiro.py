from src import financeiro


def test_calcular_item_valores_corretos():
    resultado = financeiro.calcular_item(2, 45.0, 18.0)

    assert resultado["receita"] == 90.0
    assert resultado["custo"] == 36.0
    assert resultado["lucro"] == 54.0


def test_calcular_resumo_pedido_soma_multiplos_itens():
    itens = [
        {"quantidade": 2, "preco_unitario": 45.0, "custo_unitario": 18.0},
        {"quantidade": 1, "preco_unitario": 32.0, "custo_unitario": 12.5},
    ]
    resumo = financeiro.calcular_resumo_pedido(itens)

    assert resumo["receita_total"] == 122.0
    assert resumo["custo_total"] == 48.5
    assert resumo["lucro_total"] == 73.5
    assert resumo["margem_percentual"] == round(73.5 / 122.0 * 100, 2)


def test_calcular_resumo_pedido_sem_itens_nao_gera_divisao_por_zero():
    resumo = financeiro.calcular_resumo_pedido([])

    assert resumo["receita_total"] == 0.0
    assert resumo["margem_percentual"] == 0.0


def test_calcular_resumo_periodo_agrega_por_pedido_unico():
    linhas = [
        {"pedido_id": 1, "receita": 90.0, "custo_total": 36.0, "lucro": 54.0},
        {"pedido_id": 1, "receita": 32.0, "custo_total": 12.5, "lucro": 19.5},
        {"pedido_id": 2, "receita": 39.9, "custo_total": 15.0, "lucro": 24.9},
    ]
    resumo = financeiro.calcular_resumo_periodo(linhas)

    assert resumo["quantidade_pedidos"] == 2  # pedidos distintos, não linhas
    assert resumo["receita_total"] == round(90.0 + 32.0 + 39.9, 2)
    assert resumo["lucro_total"] == round(54.0 + 19.5 + 24.9, 2)


def test_calcular_resumo_periodo_lista_vazia_nao_quebra():
    resumo = financeiro.calcular_resumo_periodo([])
    assert resumo["receita_total"] == 0.0
    assert resumo["margem_percentual"] == 0.0
    assert resumo["quantidade_pedidos"] == 0
