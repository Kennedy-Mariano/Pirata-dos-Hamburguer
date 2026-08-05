"""
Servidor que recebe os pedidos em tempo real via webhook do WhatsApp Business Cloud API.

Como usar:
1. Rode este arquivo: python app.py
2. Exponha a porta publicamente (ex.: ngrok http 5000) durante o desenvolvimento.
3. Cadastre a URL pública + WHATSAPP_VERIFY_TOKEN no painel da Meta (Webhooks).

Cada mensagem recebida no formato "PEDIDO: 2x Camiseta Basica Branca" é
processada automaticamente pelo pipeline (estoque -> financeiro -> Power BI -> PDF -> e-mail -> confirmação).
"""
from flask import Flask, request, jsonify
from src import config, db, whatsapp
from src.pipeline import processar_pedido

app = Flask(__name__)


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Endpoint de verificação exigido pela Meta ao cadastrar o webhook."""
    modo = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    desafio = request.args.get("hub.challenge")

    if modo == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return desafio, 200
    return "Token de verificação inválido", 403


@app.route("/webhook", methods=["POST"])
def receber_webhook():
    """Recebe as mensagens novas enviadas pelos clientes no WhatsApp."""
    payload = request.get_json(silent=True) or {}
    dados = whatsapp.interpretar_webhook(payload)

    if not dados:
        return jsonify({"status": "ignorado"}), 200

    itens_pedido_texto = whatsapp.interpretar_pedido_simples(dados["texto"])
    if not itens_pedido_texto:
        whatsapp.enviar_mensagem(
            dados["telefone"],
            "Olá! Para fazer um pedido, envie no formato:\n"
            "PEDIDO: 2x Camiseta Basica Branca, 1x Caneca Personalizada",
        )
        return jsonify({"status": "instrucoes_enviadas"}), 200

    resultado = processar_pedido(
        cliente_nome=dados["nome"],
        cliente_telefone=dados["telefone"],
        itens_pedido_texto=itens_pedido_texto,
    )
    return jsonify(resultado), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
