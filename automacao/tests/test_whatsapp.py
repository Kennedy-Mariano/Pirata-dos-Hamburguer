from src import whatsapp


def test_interpretar_pedido_simples_um_item():
    itens = whatsapp.interpretar_pedido_simples("PEDIDO: 2x Camiseta Basica Branca")
    assert itens == [{"nome_produto": "Camiseta Basica Branca", "quantidade": 2}]


def test_interpretar_pedido_simples_multiplos_itens():
    itens = whatsapp.interpretar_pedido_simples(
        "PEDIDO: 2x Camiseta Basica Branca, 1x Caneca Personalizada"
    )
    assert itens == [
        {"nome_produto": "Camiseta Basica Branca", "quantidade": 2},
        {"nome_produto": "Caneca Personalizada", "quantidade": 1},
    ]


def test_interpretar_pedido_simples_texto_sem_prefixo_pedido_retorna_vazio():
    assert whatsapp.interpretar_pedido_simples("Oi, tudo bem?") == []


def test_interpretar_pedido_simples_ignora_item_mal_formatado():
    # "abc" não tem quantidade numérica válida antes do "x" -> deve ser ignorado
    itens = whatsapp.interpretar_pedido_simples("PEDIDO: abcx Caneca, 3x Bone Aba Reta")
    assert itens == [{"nome_produto": "Bone Aba Reta", "quantidade": 3}]


def test_interpretar_webhook_extrai_telefone_nome_e_texto():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": "Maria"}}],
                    "messages": [{"from": "5541999999999", "text": {"body": "PEDIDO: 1x Bone Aba Reta"}}],
                }
            }]
        }]
    }
    dados = whatsapp.interpretar_webhook(payload)
    assert dados == {
        "telefone": "5541999999999",
        "nome": "Maria",
        "texto": "PEDIDO: 1x Bone Aba Reta",
    }


def test_interpretar_webhook_payload_invalido_retorna_none():
    assert whatsapp.interpretar_webhook({}) is None
    assert whatsapp.interpretar_webhook({"entry": []}) is None


def test_montar_mensagem_confirmacao_contem_dados_essenciais():
    resumo = {"receita_total": 122.0}
    mensagem = whatsapp.montar_mensagem_confirmacao("Maria", 7, resumo)
    assert "Maria" in mensagem
    assert "#7" in mensagem
    assert "122.00" in mensagem


def test_enviar_mensagem_modo_teste_sem_credenciais(monkeypatch):
    monkeypatch.setattr(whatsapp.config, "WHATSAPP_TOKEN", "")
    monkeypatch.setattr(whatsapp.config, "WHATSAPP_PHONE_NUMBER_ID", "")
    resultado = whatsapp.enviar_mensagem("5541999999999", "oi")
    assert resultado == {"modo": "teste", "enviado": False}
