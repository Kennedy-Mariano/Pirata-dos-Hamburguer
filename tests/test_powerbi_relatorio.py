import os
import csv
from datetime import datetime

from src import powerbi_export, relatorio


LINHAS_EXEMPLO = [
    {
        "pedido_id": 1, "produto": "Camiseta Basica Branca", "quantidade": 2,
        "receita": 90.0, "custo_total": 36.0, "lucro": 54.0,
        "data_pedido": datetime(2026, 7, 30, 18, 0),
    },
    {
        "pedido_id": 1, "produto": "Caneca Personalizada", "quantidade": 1,
        "receita": 32.0, "custo_total": 12.5, "lucro": 19.5,
        "data_pedido": datetime(2026, 7, 30, 18, 0),
    },
]


def test_exportar_csv_gera_arquivo_com_colunas_esperadas(tmp_path):
    caminho = powerbi_export.exportar_csv(LINHAS_EXEMPLO, str(tmp_path))

    assert os.path.exists(caminho)
    with open(caminho, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))

    assert len(linhas) == 2
    assert linhas[0]["produto"] == "Camiseta Basica Branca"
    assert float(linhas[0]["receita"]) == 90.0


def test_exportar_csv_lista_vazia_nao_quebra(tmp_path):
    caminho = powerbi_export.exportar_csv([], str(tmp_path))
    assert os.path.exists(caminho)


def test_enviar_streaming_dataset_modo_teste_sem_url(monkeypatch):
    monkeypatch.setattr(powerbi_export.config, "POWERBI_PUSH_URL", "")
    assert powerbi_export.enviar_streaming_dataset(LINHAS_EXEMPLO) is False


def test_gerar_relatorio_pdf_cria_arquivo(tmp_path):
    produtos_para_repor = [
        {"nome": "Caneca Personalizada", "quantidade_estoque": 3, "estoque_minimo": 8, "quantidade_faltante": 5},
    ]
    resumo = {"receita_total": 122.0, "custo_total": 48.5, "lucro_total": 73.5, "margem_percentual": 60.25}

    caminho = relatorio.gerar_relatorio_pdf(produtos_para_repor, resumo, LINHAS_EXEMPLO, str(tmp_path))

    assert os.path.exists(caminho)
    assert caminho.endswith(".pdf")
    assert os.path.getsize(caminho) > 0


def test_gerar_relatorio_pdf_sem_produtos_para_repor_e_sem_vendas(tmp_path):
    caminho = relatorio.gerar_relatorio_pdf([], {"receita_total": 0, "custo_total": 0, "lucro_total": 0, "margem_percentual": 0}, [], str(tmp_path))
    assert os.path.exists(caminho)
