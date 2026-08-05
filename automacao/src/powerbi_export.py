"""
Disponibiliza os dados de vendas, custo e lucro para o Power BI, de duas formas:

1) CSV local (mais simples): o Power BI Desktop conecta com "Obter Dados > Texto/CSV"
   e você agenda a atualização, ou usa o Power BI Gateway para ler o arquivo.

2) Streaming dataset (tempo real): se você criar um "Streaming dataset" no
   Power BI Service e configurar POWERBI_PUSH_URL no .env, os dados são
   enviados automaticamente via API a cada execução (push API).
"""
import os
import requests
import pandas as pd
from src import config


def exportar_csv(linhas_powerbi, pasta_saida) -> str:
    os.makedirs(pasta_saida, exist_ok=True)
    caminho = os.path.join(pasta_saida, "dados_powerbi.csv")

    df = pd.DataFrame(linhas_powerbi)
    if not df.empty:
        for coluna in ["receita", "custo_total", "lucro", "preco_unitario", "custo_unitario"]:
            if coluna in df.columns:
                df[coluna] = df[coluna].astype(float)

    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho


def enviar_streaming_dataset(linhas_powerbi) -> bool:
    """Envia os dados para um Streaming Dataset do Power BI via Push API (tempo real)."""
    if not config.POWERBI_PUSH_URL:
        print("[POWER BI - MODO TESTE] POWERBI_PUSH_URL não configurada; use o CSV exportado.")
        return False

    linhas_formatadas = []
    for linha in linhas_powerbi:
        linhas_formatadas.append({
            "pedido_id": linha["pedido_id"],
            "produto": linha["produto"],
            "quantidade": linha["quantidade"],
            "receita": float(linha["receita"]),
            "custo_total": float(linha["custo_total"]),
            "lucro": float(linha["lucro"]),
            "data_pedido": str(linha["data_pedido"]),
        })

    resposta = requests.post(config.POWERBI_PUSH_URL, json=linhas_formatadas, timeout=15)
    resposta.raise_for_status()
    return True
