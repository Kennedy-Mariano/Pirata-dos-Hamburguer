"""
Geração automática do relatório em PDF com:
- produtos que precisam de reposição
- resumo financeiro (receita, custo e lucro) do período
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def gerar_relatorio_pdf(produtos_para_repor, resumo_financeiro, linhas_powerbi, pasta_saida):
    os.makedirs(pasta_saida, exist_ok=True)
    agora = datetime.now()
    nome_arquivo = f"relatorio_estoque_{agora.strftime('%Y%m%d_%H%M')}.pdf"
    caminho = os.path.join(pasta_saida, nome_arquivo)

    doc = SimpleDocTemplate(caminho, pagesize=A4,
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle("titulo", parent=estilos["Title"], fontSize=16, textColor=colors.HexColor("#1565C0"))
    subtitulo_estilo = ParagraphStyle("subtitulo", parent=estilos["Heading2"], fontSize=12, textColor=colors.HexColor("#1565C0"))

    elementos = []
    elementos.append(Paragraph("Relatório de Estoque, Vendas e Lucro", titulo_estilo))
    elementos.append(Paragraph(f"Gerado automaticamente em {agora.strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]))
    elementos.append(Spacer(1, 0.6 * cm))

    # ---- Resumo financeiro ----
    elementos.append(Paragraph("Resumo Financeiro do Período", subtitulo_estilo))
    dados_resumo = [
        ["Receita total", "Custo total", "Lucro total", "Margem"],
        [
            f"R$ {resumo_financeiro['receita_total']:.2f}",
            f"R$ {resumo_financeiro['custo_total']:.2f}",
            f"R$ {resumo_financeiro['lucro_total']:.2f}",
            f"{resumo_financeiro['margem_percentual']:.1f}%",
        ],
    ]
    tabela_resumo = Table(dados_resumo, colWidths=[4 * cm] * 4)
    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    elementos.append(tabela_resumo)
    elementos.append(Spacer(1, 0.8 * cm))

    # ---- Produtos que precisam de reposição ----
    elementos.append(Paragraph("Produtos que Precisam de Reposição", subtitulo_estilo))
    if produtos_para_repor:
        dados_reposicao = [["Produto", "Estoque atual", "Estoque mínimo", "Quantidade a repor"]]
        for produto in produtos_para_repor:
            dados_reposicao.append([
                produto["nome"],
                str(produto["quantidade_estoque"]),
                str(produto["estoque_minimo"]),
                str(produto["quantidade_faltante"]),
            ])
        tabela_reposicao = Table(dados_reposicao, colWidths=[7 * cm, 3.3 * cm, 3.3 * cm, 3.4 * cm])
        tabela_reposicao.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EF6C00")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBEBD9")]),
        ]))
        elementos.append(tabela_reposicao)
    else:
        elementos.append(Paragraph("Nenhum produto abaixo do estoque mínimo no momento.", estilos["Normal"]))

    elementos.append(Spacer(1, 0.8 * cm))

    # ---- Detalhamento por pedido/produto (o que também alimenta o Power BI) ----
    elementos.append(Paragraph("Detalhamento de Vendas (base usada no Power BI)", subtitulo_estilo))
    if linhas_powerbi:
        dados_vendas = [["Pedido", "Produto", "Qtd", "Receita", "Custo", "Lucro"]]
        for linha in linhas_powerbi[:25]:  # limita para não estourar o PDF em bases grandes
            dados_vendas.append([
                str(linha["pedido_id"]),
                linha["produto"],
                str(linha["quantidade"]),
                f"R$ {float(linha['receita']):.2f}",
                f"R$ {float(linha['custo_total']):.2f}",
                f"R$ {float(linha['lucro']):.2f}",
            ])
        tabela_vendas = Table(dados_vendas, colWidths=[2 * cm, 5.5 * cm, 1.5 * cm, 3 * cm, 3 * cm, 3 * cm])
        tabela_vendas.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8F5E9")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ]))
        elementos.append(tabela_vendas)
    else:
        elementos.append(Paragraph("Nenhuma venda registrada no período.", estilos["Normal"]))

    doc.build(elementos)
    return caminho
