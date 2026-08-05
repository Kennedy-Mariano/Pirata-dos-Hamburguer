"""
Execução manual/agendada da automação (sem depender do webhook do WhatsApp).

Uso:
    python main.py                -> roda a rotina de reposição + relatório + Power BI uma vez
    python main.py --agendar      -> deixa rodando e executa automaticamente todo dia às 18h
"""
import sys
import schedule
import time
from src import db, estoque, financeiro, relatorio, email_sender, powerbi_export, config


def rotina_diaria():
    print("Iniciando rotina de automação...")
    conn = db.get_connection()
    try:
        produtos = db.buscar_produtos(conn)
        produtos_para_repor = estoque.verificar_reposicao(produtos)
        for produto in produtos_para_repor:
            db.registrar_alerta_reposicao(conn, produto["id"], produto["quantidade_estoque"], produto["estoque_minimo"])
            print(f"  -> Repor: {produto['nome']} (faltam {produto['quantidade_faltante']} unidades)")

        linhas_powerbi = db.buscar_dados_powerbi(conn)
        caminho_csv = powerbi_export.exportar_csv(linhas_powerbi, config.PASTA_DADOS)
        powerbi_export.enviar_streaming_dataset(linhas_powerbi)
        print(f"  -> Dados do Power BI exportados em: {caminho_csv}")

        resumo_periodo = financeiro.calcular_resumo_periodo(linhas_powerbi)
        caminho_pdf = relatorio.gerar_relatorio_pdf(produtos_para_repor, resumo_periodo, linhas_powerbi, config.PASTA_RELATORIOS)
        print(f"  -> Relatório gerado em: {caminho_pdf}")

        email_sender.enviar_email_relatorio(caminho_pdf, resumo_periodo)
        print("  -> E-mail processado.")
        print(f"  -> Lucro total do período: R$ {resumo_periodo['lucro_total']:.2f}")
    finally:
        conn.close()
    print("Rotina finalizada.\n")


if __name__ == "__main__":
    if "--agendar" in sys.argv:
        schedule.every().day.at("18:00").do(rotina_diaria)
        print("Agendador ativo. A rotina roda todos os dias às 18:00. (Ctrl+C para sair)")
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        rotina_diaria()
