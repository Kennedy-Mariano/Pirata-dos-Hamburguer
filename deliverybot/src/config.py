import os
from dotenv import load_dotenv

load_dotenv()

# --- Provedor de WhatsApp: "TESTE" (padrão), "WAHA" ou "META" ---
# WAHA = WhatsApp HTTP API self-hosted via Docker (login por QR Code, sem
#        precisar de conta comercial verificada na Meta) -> ver README.
# META = WhatsApp Business Cloud API oficial (precisa de app + token da Meta).
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "TESTE").strip().upper()

# --- WhatsApp Business Cloud API (Meta) ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "trocar_por_uma_palavra_secreta").strip()
WHATSAPP_API_URL = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# --- WAHA (WhatsApp HTTP API) ---
WAHA_URL = os.getenv("WAHA_URL", "http://localhost:3000").rstrip("/")
WAHA_SESSION = os.getenv("WAHA_SESSION", "default").strip()
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "").strip()  # opcional, se você configurar auth no WAHA

if WHATSAPP_PROVIDER == "WAHA":
    MODO_TESTE = False
elif WHATSAPP_PROVIDER == "META":
    MODO_TESTE = not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID)
else:
    MODO_TESTE = True

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")

# --- Restaurante ---
NOME_RESTAURANTE = os.getenv("NOME_RESTAURANTE", "Barbaros Lanches")
TELEFONE_RESTAURANTE = os.getenv("TELEFONE_RESTAURANTE", "(47) 3000-0000")
ENDERECO_RESTAURANTE = os.getenv("ENDERECO_RESTAURANTE", "Rua das Hamburguerias, 123 - Centro")
HORARIO_FUNCIONAMENTO = os.getenv("HORARIO_FUNCIONAMENTO", "Terça a Domingo, das 18h às 23h30")
TAXA_ENTREGA = float(os.getenv("TAXA_ENTREGA", "6.00"))
CEP_RESTAURANTE = os.getenv("CEP_RESTAURANTE", "89460-000")
RAIO_ENTREGA_KM = float(os.getenv("RAIO_ENTREGA_KM", "6"))

# --- Banco de dados ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/deliverybot.db")

# --- Operação ---
TEMPO_PREPARO_MIN = int(os.getenv("TEMPO_PREPARO_MIN", "40"))
VALIDADE_LINK_MIN = int(os.getenv("VALIDADE_LINK_MIN", "30"))
