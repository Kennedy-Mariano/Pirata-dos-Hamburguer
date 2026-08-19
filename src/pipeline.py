"""
Pipeline central da automação. Implementa exatamente o fluxo descrito no
projeto (item 7 - Como Funcionará a Automação / item 10 - Fluxograma):

1. Conecta ao PostgreSQL
2. Busca os produtos do pedido e verifica estoque
3. Registra o pedido e dá baixa no estoque
4. Verifica reposição (estoque atual x estoque mínimo)
5. Calcula custo efetivo, receita e lucro
6. Atualiza a base usada pelo Power BI
7. Gera o relatório em PDF
8. Envia o relatório por e-mail
9. Envia a confirmação do pedido ao cliente via WhatsApp
"""
from src import db, estoque, financeiro, relatorio, email_sender, powerbi_export, whatsapp, config
from src import orders


def processar_pedido(cliente_nome: str, cliente_telefone: str, itens_pedido_texto: list) -> dict:
    conn = db.get_connection()
    try:
        # 1) resolve os produtos citados no pedido (pelo nome) para seus IDs
        itens_para_criar = []
        itens_calculo = []
        produtos_nao_encontrados = []

        for item_texto in itens_pedido_texto:
            produto = db.buscar_produto_por_nome(conn, item_texto["nome_produto"])
            if not produto:
                produtos_nao_encontrados.append(item_texto["nome_produto"])
                continue

            quantidade = item_texto["quantidade"]
            if not estoque.produto_tem_estoque_suficiente(produto, quantidade):
                quantidade = produto["quantidade_estoque"]  # atende com o que tiver disponível

            if quantidade <= 0:
                continue

            itens_para_criar.append({"produto_id": produto["id"], "quantidade": quantidade})
            itens_calculo.append({
                "quantidade": quantidade,
                "preco_unitario": float(produto["preco_venda"]),
                "custo_unitario": float(produto["custo_unitario"]),
            })

        if not itens_para_criar:
            return {"status": "erro", "motivo": "nenhum produto válido encontrado", "nao_encontrados": produtos_nao_encontrados}

        # 2) cria o pedido e dá baixa automática no estoque
        pedido_id = db.criar_pedido(conn, cliente_nome, cliente_telefone, itens_para_criar)

        # 3) recalcula estoque e verifica reposição
        produtos_atualizados = db.buscar_produtos(conn)
        produtos_para_repor = estoque.verificar_reposicao(produtos_atualizados)
        for produto in produtos_para_repor:
            db.registrar_alerta_reposicao(conn, produto["id"], produto["quantidade_estoque"], produto["estoque_minimo"])

        # 4) calcula o custo efetivo, receita e lucro do pedido
        resumo_pedido = financeiro.calcular_resumo_pedido(itens_calculo)

        # 5) atualiza a base usada pelo Power BI (todas as vendas até agora)
        linhas_powerbi = db.buscar_dados_powerbi(conn)
        powerbi_export.exportar_csv(linhas_powerbi, config.PASTA_DADOS)
        powerbi_export.enviar_streaming_dataset(linhas_powerbi)

        # 6) gera o relatório em PDF com a foto geral do negócio
        resumo_periodo = financeiro.calcular_resumo_periodo(linhas_powerbi)
        caminho_pdf = relatorio.gerar_relatorio_pdf(
            produtos_para_repor, resumo_periodo, linhas_powerbi, config.PASTA_RELATORIOS
        )

        # 7) envia o relatório por e-mail ao responsável
        email_sender.enviar_email_relatorio(caminho_pdf, resumo_periodo)

        # 8) cria token single-use e envia link via WhatsApp
        conn_for_token = conn  # já temos conexão aberta
        token = orders.create_single_use_token(conn_for_token, pedido_id)
        host = getattr(config, 'WHATSAPP_PUBLIC_HOST', '').rstrip('/') if getattr(config, 'WHATSAPP_PUBLIC_HOST', '') else None
        if host:
            link = f"{host}/redeem/{token}"
        else:
            link = f"/redeem/{token} (configure WHATSAPP_PUBLIC_HOST no .env para gerar link completo)"

        mensagem = (
            whatsapp.montar_mensagem_confirmacao(cliente_nome, pedido_id, resumo_pedido)
            + "\n\n"
            + "Abra o link abaixo para visualizar/baixar o recibo do pedido (uso único):\n"
            + link
        )
        whatsapp.enviar_mensagem(cliente_telefone, mensagem)

        return {
            "status": "ok",
            "pedido_id": pedido_id,
            "resumo_pedido": resumo_pedido,
            "produtos_para_repor": [p["nome"] for p in produtos_para_repor],
            "relatorio_pdf": caminho_pdf,
            "nao_encontrados": produtos_nao_encontrados,
        }
    finally:
        conn.close()
