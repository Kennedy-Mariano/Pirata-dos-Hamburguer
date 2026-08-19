"""
Configurações centrais do projeto.
Lê as variáveis do arquivo .env (copie o .env.example para .env e preencha).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Banco de dados
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "automacao_estoque")
DB_USER = os.getenv("DB_USER", "automacao")
DB_PASSWORD = os.getenv("DB_PASSWORD", "automacao123")

# WhatsApp Business Cloud API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# E-mail
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP", "")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", "")

# Power BI
POWERBI_PUSH_URL = os.getenv("POWERBI_PUSH_URL", "")

# Pastas de saída
PASTA_RELATORIOS = os.path.join(os.path.dirname(__file__), "..", "relatorios")
PASTA_DADOS = os.path.join(os.path.dirname(__file__), "..", "data")

# Token single-use (minutos)
SINGLE_USE_TOKEN_TTL_MINUTES = int(os.getenv("SINGLE_USE_TOKEN_TTL_MINUTES", "60"))
