"""Integração com o WhatsApp. Suporta dois provedores, escolhidos por
WHATSAPP_PROVIDER no .env:

- WAHA  -> WhatsApp HTTP API self-hosted via Docker (github.com/devlikeapro/waha).
           Login por QR Code, sem precisar de conta comercial verificada.
           Inspirado no vídeo "N8N + WhatsApp GRÁTIS" (que usa WAHA por trás
           do N8N) — aqui a mesma API é chamada direto do Python.
- META  -> WhatsApp Business Cloud API oficial (precisa de app + token da Meta).
- TESTE -> nenhum provedor configurado: mensagens só aparecem no console.
"""
import requests

from . import config


def _numero_limpo(telefone: str) -> str:
    """Remove @c.us, espaços, '+', etc. Deixa só os dígitos do telefone."""
    return "".join(ch for ch in telefone if ch.isdigit())


def enviar_mensagem(telefone: str, texto: str) -> dict:
    if config.MODO_TESTE:
        print(f"[MODO TESTE] enviaria para {telefone}:\n{texto}\n{'-' * 40}")
        return {"modo_teste": True}

    try:
        if config.WHATSAPP_PROVIDER == "WAHA":
            return _enviar_via_waha(telefone, texto)
        return _enviar_via_meta(telefone, texto)
    except requests.RequestException as exc:
        # Não derruba o webhook/pedido: o WAHA reenvia o evento se o Flask
        # responder 500, e o pedido já pode ter sido gravado no banco.
        detalhe = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            detalhe = f" {resp.status_code} {resp.text}"
        print(f"[WhatsApp] falha ao enviar para {telefone}:{detalhe}\n{texto}\n{'-' * 40}")
        return {"erro": str(exc), "detalhe": detalhe.strip()}


def _enviar_via_waha(telefone: str, texto: str) -> dict:
    chat_id = f"{_numero_limpo(telefone)}@c.us"
    payload = {"session": config.WAHA_SESSION, "chatId": chat_id, "text": texto}
    headers = {"Content-Type": "application/json"}
    if config.WAHA_API_KEY:
        headers["X-Api-Key"] = config.WAHA_API_KEY

    resp = requests.post(f"{config.WAHA_URL}/api/sendText", json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def _enviar_via_meta(telefone: str, texto: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": _numero_limpo(telefone),
        "type": "text",
        "text": {"body": texto, "preview_url": True},
    }
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(config.WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"[META] erro ao enviar mensagem para {telefone}: {resp.text}")
        raise
    return resp.json()


# ---------------------------------------------------------------------------
# Leitura das mensagens recebidas (formato de webhook difere por provedor)
# ---------------------------------------------------------------------------

def extrair_mensagem_recebida_meta(payload: dict) -> dict | None:
    """Extrai {telefone, texto, nome} do payload de webhook da Meta Cloud API."""
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        mensagens = change.get("messages")
        if not mensagens:
            return None

        msg = mensagens[0]
        telefone = msg["from"]
        nome = change.get("contacts", [{}])[0].get("profile", {}).get("name", "Cliente")

        if msg.get("type") == "text":
            texto = msg["text"]["body"]
        elif msg.get("type") == "interactive":
            interativo = msg["interactive"]
            if interativo.get("type") == "button_reply":
                texto = interativo["button_reply"]["title"]
            elif interativo.get("type") == "list_reply":
                texto = interativo["list_reply"]["title"]
            else:
                texto = ""
        else:
            texto = ""

        return {"telefone": telefone, "texto": texto.strip(), "nome": nome}
    except (KeyError, IndexError, TypeError):
        return None


def extrair_mensagem_recebida_waha(payload: dict) -> dict | None:
    """Extrai {telefone, texto, nome} do payload de webhook do WAHA.

    Formato típico do evento 'message' do WAHA:
    {
      "event": "message",
      "session": "default",
      "payload": {
        "from": "5511999999999@c.us",
        "body": "texto da mensagem",
        "fromMe": false,
        "_data": {"notifyName": "Nome do contato"}, ...
      }
    }
    """
    try:
        if payload.get("event") != "message":
            return None

        dados = payload["payload"]
        if dados.get("fromMe"):
            return None  # ignora eco de mensagens enviadas pelo próprio bot

        telefone = _numero_limpo(dados.get("from", ""))
        texto = (dados.get("body") or "").strip()
        nome = (
            dados.get("_data", {}).get("notifyName")
            or dados.get("notifyName")
            or "Cliente"
        )

        if not telefone:
            return None

        return {"telefone": telefone, "texto": texto, "nome": nome}
    except (KeyError, TypeError):
        return None


def extrair_mensagem_recebida(payload: dict) -> dict | None:
    """Detecta automaticamente se o payload veio da Meta ou do WAHA."""
    if "event" in payload and "payload" in payload:
        return extrair_mensagem_recebida_waha(payload)
    return extrair_mensagem_recebida_meta(payload)
