from src import estoque


def test_verificar_reposicao_retorna_apenas_produtos_abaixo_do_minimo():
    produtos = [
        {"id": 1, "nome": "Caneca", "quantidade_estoque": 3, "estoque_minimo": 8},
        {"id": 2, "nome": "Camiseta", "quantidade_estoque": 40, "estoque_minimo": 10},
    ]
    resultado = estoque.verificar_reposicao(produtos)

    assert len(resultado) == 1
    assert resultado[0]["nome"] == "Caneca"
    assert resultado[0]["quantidade_faltante"] == 5


def test_verificar_reposicao_inclui_produto_no_limite_exato():
    produtos = [{"id": 1, "nome": "Bone", "quantidade_estoque": 6, "estoque_minimo": 6}]
    resultado = estoque.verificar_reposicao(produtos)

    assert len(resultado) == 1
    assert resultado[0]["quantidade_faltante"] == 0


def test_verificar_reposicao_sem_produtos_para_repor():
    produtos = [{"id": 1, "nome": "Garrafa", "quantidade_estoque": 15, "estoque_minimo": 5}]
    assert estoque.verificar_reposicao(produtos) == []


def test_produto_tem_estoque_suficiente_true():
    produto = {"quantidade_estoque": 10}
    assert estoque.produto_tem_estoque_suficiente(produto, 5) is True


def test_produto_tem_estoque_suficiente_false():
    produto = {"quantidade_estoque": 2}
    assert estoque.produto_tem_estoque_suficiente(produto, 5) is False


def test_produto_tem_estoque_suficiente_limite_exato():
    produto = {"quantidade_estoque": 5}
    assert estoque.produto_tem_estoque_suficiente(produto, 5) is True
