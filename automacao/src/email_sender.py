"""
Envio automático do relatório em PDF por e-mail ao responsável.
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from src import config


def enviar_email_relatorio(caminho_pdf: str, resumo_financeiro: dict, destinatario: str = None) -> bool:
    destinatario = destinatario or config.EMAIL_DESTINATARIO

    if not config.EMAIL_REMETENTE or not config.EMAIL_SENHA_APP or not destinatario:
        print(f"[EMAIL - MODO TESTE] Relatório '{os.path.basename(caminho_pdf)}' seria enviado para {destinatario}")
        return False

    msg = MIMEMultipart()
    msg["From"] = config.EMAIL_REMETENTE
    msg["To"] = destinatario
    msg["Subject"] = "Relatório automático de estoque, vendas e lucro"

    corpo = f"""
Olá,

Segue em anexo o relatório automático gerado pelo sistema.

Resumo do período:
- Receita total: R$ {resumo_financeiro['receita_total']:.2f}
- Custo total:   R$ {resumo_financeiro['custo_total']:.2f}
- Lucro total:   R$ {resumo_financeiro['lucro_total']:.2f}
- Margem:        {resumo_financeiro['margem_percentual']:.1f}%

Este é um e-mail automático, não é necessário responder.
"""
    msg.attach(MIMEText(corpo, "plain"))

    with open(caminho_pdf, "rb") as arquivo:
        parte = MIMEBase("application", "octet-stream")
        parte.set_payload(arquivo.read())
    encoders.encode_base64(parte)
    parte.add_header("Content-Disposition", f"attachment; filename={os.path.basename(caminho_pdf)}")
    msg.attach(parte)

    with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as servidor:
        servidor.starttls()
        servidor.login(config.EMAIL_REMETENTE, config.EMAIL_SENHA_APP)
        servidor.send_message(msg)

    return True
