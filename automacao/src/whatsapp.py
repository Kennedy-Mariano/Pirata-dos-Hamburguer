"""
Integração com a API do WhatsApp Business (Meta Cloud API).

- receber_pedido(): interpreta a mensagem recebida no webhook e transforma em um pedido.
- enviar_mensagem(): envia uma mensagem de texto para o cliente (ex.: confirmação do pedido).

Documentação oficial: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import requests
from src import config


def enviar_mensagem(telefone_destino: str, texto: str) -> dict:
    """
    Envia uma mensagem de texto simples via WhatsApp Business Cloud API.
    Requer WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID configurados no .env.
    """
    if not config.WHATSAPP_TOKEN or not config.WHATSAPP_PHONE_NUMBER_ID:
        print(f"[WHATSAPP - MODO TESTE] Para {telefone_destino}: {texto}")
        return {"modo": "teste", "enviado": False}

    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone_destino,
        "type": "text",
        "text": {"body": texto},
    }
    resposta = requests.post(config.WHATSAPP_API_URL, headers=headers, json=payload, timeout=15)
    resposta.raise_for_status()
    return resposta.json()


def montar_mensagem_confirmacao(cliente_nome: str, pedido_id: int, resumo: dict) -> str:
    return (
        f"Olá, {cliente_nome}! ✅\n"
        f"Recebemos seu pedido #{pedido_id}.\n"
        f"Valor total: R$ {resumo['receita_total']:.2f}\n"
        f"Em breve entraremos em contato para combinar a entrega. Obrigado pela preferência!"
    )


def interpretar_webhook(payload: dict):
    """
    Extrai a mensagem de texto e o telefone do remetente a partir do payload
    enviado pela Meta quando chega uma nova mensagem no webhook.

    Formato oficial (resumido):
    payload["entry"][0]["changes"][0]["value"]["messages"][0]
    """
    try:
        valor = payload["entry"][0]["changes"][0]["value"]
        mensagem = valor["messages"][0]
        telefone = mensagem["from"]
        texto = mensagem.get("text", {}).get("body", "").strip()
        nome_contato = valor["contacts"][0]["profile"]["name"]
        return {"telefone": telefone, "nome": nome_contato, "texto": texto}
    except (KeyError, IndexError):
        return None


def interpretar_pedido_simples(texto: str):
    """
    Interpreta mensagens no formato simples:
        "PEDIDO: 2x Camiseta Basica Branca, 1x Caneca Personalizada"
    Retorna uma lista de {"nome_produto": ..., "quantidade": ...}
    Isso pode ser evoluído depois para um menu interativo (botões/listas do WhatsApp).
    """
    itens = []
    if not texto.upper().startswith("PEDIDO"):
        return itens

    conteudo = texto.split(":", 1)[-1]
    partes = [p.strip() for p in conteudo.split(",") if p.strip()]
    for parte in partes:
        if "x" in parte.lower():
            qtd_str, nome = parte.lower().split("x", 1)
            try:
                quantidade = int(qtd_str.strip())
                itens.append({"nome_produto": nome.strip().title(), "quantidade": quantidade})
            except ValueError:
                continue
    return itens
