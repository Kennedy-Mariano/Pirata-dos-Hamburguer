import hmac
import ipaddress
import logging
import threading
from functools import wraps

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from . import bot, cardapio, config, fila, pedidos, recibo, viacep, waha_admin, whatsapp
from .db import init_db
from .ia import aquecer_ollama
from .links import link_valido, marcar_link_usado, obter_link

logging.basicConfig(
    level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="../web/templates",
    static_folder="../web/static",
    static_url_path="/static",
)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

# Banco e IA são inicializados UMA VEZ ao importar o módulo (não a cada
# requisição -- rodar o schema inteiro e checar o cardápio em todo request
# era um desperdício de I/O sem necessidade nenhuma).
init_db()
app.jinja_env.globals["icone_categoria"] = cardapio.icone_categoria
if config.IA_PROVIDER == "OLLAMA" and config.OLLAMA_AQUECER_AO_INICIAR:
    threading.Thread(target=aquecer_ollama, daemon=True).start()


# ---------------------------------------------------------------------------
# Segurança: segredo embutido na URL dos webhooks + HTTP Basic Auth no painel
# da cozinha. Ver MANUAL.md, seção "Segurança", para como configurar.
# ---------------------------------------------------------------------------

def _segredo_valido(segredo_recebido: str) -> bool:
    if not config.WEBHOOK_SECRET:
        # Sem segredo configurado, o endpoint fica bloqueado por padrão --
        # é melhor "esquecer de configurar e nada funcionar" do que "esquecer
        # de configurar e o endpoint ficar aberto pra qualquer um".
        return False
    return hmac.compare_digest(segredo_recebido or "", config.WEBHOOK_SECRET)


def _exigir_autenticacao_cozinha():
    auth = request.authorization
    usuario_ok = bool(config.COZINHA_USUARIO and config.COZINHA_SENHA)
    if not usuario_ok:
        logger.warning("Acesso à cozinha bloqueado: COZINHA_USUARIO/COZINHA_SENHA não configurados no .env")
        return False
    if not auth:
        return False
    return hmac.compare_digest(auth.username or "", config.COZINHA_USUARIO) and hmac.compare_digest(
        auth.password or "", config.COZINHA_SENHA
    )


def requer_login_cozinha(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not _exigir_autenticacao_cozinha():
            return (
                "Login necessário.",
                401,
                {"WWW-Authenticate": 'Basic realm="Painel da cozinha"'},
            )
        return view(*args, **kwargs)

    return wrapper


# Docker Desktop entrega a conexão do navegador local pelo gateway da rede
# interna (172.16/12 ou 192.168.65/24), não por 127.0.0.1. A porta publicada
# continua só em 127.0.0.1. Um túnel (ngrok) manda X-Forwarded-For e cai fora.
_REDES_DO_NOTEBOOK = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.65.0/24"),
)


def _acesso_local_sem_proxy() -> bool:
    veio_de_proxy = any(
        request.headers.get(h) for h in ("X-Forwarded-For", "X-Forwarded-Host", "Forwarded")
    )
    if veio_de_proxy:
        return False
    try:
        ip = ipaddress.ip_address(request.remote_addr or "")
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip in rede for rede in _REDES_DO_NOTEBOOK)


def apenas_neste_computador(view):
    """Só atende quem está NO próprio notebook. Pelo ngrok a conexão também
    chega como 127.0.0.1, mas vem com o cabeçalho X-Forwarded-For -- por isso
    ele é checado: a tela do QR Code nunca fica acessível pela internet."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not _acesso_local_sem_proxy():
            return "Esta página só abre no computador do restaurante.", 403
        return view(*args, **kwargs)

    return wrapper


def apenas_em_desenvolvimento(view):
    """Bloqueia o endpoint quando FLASK_DEBUG não está ligado -- usado nas
    rotas que existem só para testar localmente e que não devem ficar
    acessíveis quando o sistema está exposto publicamente (ngrok etc.)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not config.FLASK_DEBUG:
            return jsonify({"erro": "endpoint disponível apenas com FLASK_DEBUG=true"}), 404
        return view(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Webhook do WhatsApp (Meta Cloud API)
# ---------------------------------------------------------------------------

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    modo = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    desafio = request.args.get("hub.challenge")

    if modo == "subscribe" and hmac.compare_digest(token or "", config.WHATSAPP_VERIFY_TOKEN):
        return desafio, 200
    return "Token de verificação inválido", 403


@app.route("/webhook", methods=["POST"])
def receber_webhook():
    payload = request.get_json(silent=True) or {}
    dados = whatsapp.extrair_mensagem_recebida(payload)

    if dados is None:
        # Pode ser um evento de status (entregue/lido) ou payload vazio; apenas confirma o recebimento.
        return jsonify({"status": "ignorado"}), 200

    telefone, texto = dados["telefone"], dados["texto"]
    pedidos.registrar_mensagem(telefone, "ENTRADA", texto)

    try:
        resposta = bot.processar_mensagem(telefone, texto)
        whatsapp.enviar_mensagem(telefone, resposta)
        pedidos.registrar_mensagem(telefone, "SAIDA", resposta)
    except Exception:
        # Nunca deixa uma exceção virar uma página de erro 500 pública --
        # loga internamente e confirma o recebimento mesmo assim (evita que
        # o provedor fique retransmitindo o mesmo webhook em loop).
        logger.exception("Falha ao processar mensagem (Meta) de %s", telefone)
        return jsonify({"status": "erro_interno"}), 200

    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Webhook do WAHA (WhatsApp HTTP API self-hosted via Docker, login por QR)
#
# A URL inclui um segredo (<segredo>) como parte do caminho: só quem conhece
# WEBHOOK_SECRET (configurado no .env e usado no WHATSAPP_HOOK_URL do
# docker-compose.yml) consegue mandar requisições que o Flask aceita como
# vindas do WAHA de verdade. Ver MANUAL.md, seção "Segurança".
# ---------------------------------------------------------------------------

@app.route("/webhook/waha/<segredo>", methods=["POST"])
def receber_webhook_waha(segredo):
    if not _segredo_valido(segredo):
        logger.warning("Tentativa de acesso ao webhook do WAHA com segredo inválido")
        return jsonify({"status": "não autorizado"}), 404  # 404 em vez de 401: não revela que a rota existe

    payload = request.get_json(silent=True) or {}
    dados = whatsapp.extrair_mensagem_recebida_waha(payload)

    if dados is None:
        return jsonify({"status": "ignorado"}), 200

    telefone, texto = dados["telefone"], dados["texto"]
    chat_id = dados.get("chat_id")
    sessao = dados.get("session")
    pedidos.registrar_mensagem(telefone, "ENTRADA", texto)

    try:
        resposta = bot.processar_mensagem(telefone, texto)
        whatsapp.enviar_mensagem(telefone, resposta, chat_id=chat_id, session=sessao)
        pedidos.registrar_mensagem(telefone, "SAIDA", resposta)
    except Exception:
        # Não devolve 500 pro WAHA (evita retentativas em loop) e nunca
        # expõe o traceback -- só fica registrado no log do servidor.
        logger.exception("Falha ao processar/enviar mensagem (WAHA) de %s", telefone)
        return jsonify({"status": "erro_interno"}), 200

    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# API interna usada pelo workflow do N8N (veja n8n/deliverybot-waha.json).
# Também protegida pelo mesmo segredo do webhook -- sem isso, qualquer
# pessoa que descobrisse a URL pública poderia conversar com a IA de graça
# à sua custa, ou criar pedidos falsos.
# ---------------------------------------------------------------------------

@app.route("/api/bot/mensagem/<segredo>", methods=["POST"])
def api_processar_mensagem(segredo):
    if not _segredo_valido(segredo):
        return jsonify({"erro": "não autorizado"}), 404

    dados = request.get_json(silent=True) or {}
    telefone = whatsapp._numero_limpo(dados.get("telefone", ""))
    texto = (dados.get("texto") or "").strip()

    if not telefone:
        return jsonify({"erro": "telefone é obrigatório"}), 400

    pedidos.registrar_mensagem(telefone, "ENTRADA", texto)
    try:
        resposta = bot.processar_mensagem(telefone, texto)
    except Exception:
        logger.exception("Falha ao processar mensagem via API interna de %s", telefone)
        return jsonify({"erro": "falha ao processar mensagem"}), 500
    pedidos.registrar_mensagem(telefone, "SAIDA", resposta)

    return jsonify({"telefone": telefone, "resposta": resposta})


@app.route("/")
def inicio():
    return render_template("inicio.html", nome=config.NOME_RESTAURANTE)


# ---------------------------------------------------------------------------
# Atalho só para TESTE LOCAL: simula o cliente digitando "2" no WhatsApp,
# sem precisar de credenciais da Meta nem do webhook real. Bloqueado quando
# FLASK_DEBUG não está ligado (ver apenas_em_desenvolvimento), pra não virar
# uma forma de qualquer um gerar pedidos/custos quando o sistema está
# exposto publicamente.
# ---------------------------------------------------------------------------

@app.route("/testar", methods=["GET"])
@apenas_em_desenvolvimento
def testar_localmente():
    telefone_teste = request.args.get("telefone", "5547999990000")
    resposta = bot.processar_mensagem(telefone_teste, "2")
    pedidos.registrar_mensagem(telefone_teste, "SAIDA", resposta)
    link = resposta.replace("Faça o seu pedido em ", "").strip()
    token = link.rsplit("/", 1)[-1]
    return redirect(url_for("pagina_pedido", token=token))


# ---------------------------------------------------------------------------
# Link único de pedido: GET mostra o cardápio, POST cria o pedido
# ---------------------------------------------------------------------------

@app.route("/m/<token>", methods=["GET"])
def pagina_pedido(token):
    ok, mensagem, link = link_valido(token)
    if not ok:
        return render_template("link_invalido.html", mensagem=mensagem), 410

    produtos = cardapio.listar_produtos_ativos()
    grupos = cardapio.agrupar_por_categoria(produtos)
    return render_template(
        "pedido.html",
        token=token,
        grupos=grupos,
        nome_restaurante=config.NOME_RESTAURANTE,
        taxa_entrega=config.TAXA_ENTREGA,
    )


@app.route("/m/<token>", methods=["POST"])
def enviar_pedido(token):
    ok, mensagem, link = link_valido(token)
    if not ok:
        return render_template("link_invalido.html", mensagem=mensagem), 410

    telefone = link["telefone"]
    nome_cliente = request.form.get("nome", "Cliente").strip() or "Cliente"
    forma_pagamento = request.form.get("forma_pagamento", "Dinheiro")
    forma_entrega = request.form.get("forma_entrega", "RETIRADA BALCAO")
    cep = request.form.get("cep", "").strip()

    endereco = ""
    if forma_entrega == "ENTREGA":
        ok_cep, msg_cep, dados_cep = viacep.validar_area_entrega(cep)
        if not ok_cep:
            produtos = cardapio.listar_produtos_ativos()
            grupos = cardapio.agrupar_por_categoria(produtos)
            return render_template(
                "pedido.html",
                token=token,
                grupos=grupos,
                nome_restaurante=config.NOME_RESTAURANTE,
                taxa_entrega=config.TAXA_ENTREGA,
                erro=msg_cep,
            ), 400
        endereco = viacep.endereco_formatado(dados_cep)

    itens = []
    for chave, valor in request.form.items():
        if chave.startswith("qtd_") and valor and valor.isdigit() and int(valor) > 0:
            produto_id_str = chave.replace("qtd_", "")
            if produto_id_str.isdigit():
                itens.append({"produto_id": int(produto_id_str), "quantidade": int(valor)})

    if not itens:
        produtos = cardapio.listar_produtos_ativos()
        grupos = cardapio.agrupar_por_categoria(produtos)
        return render_template(
            "pedido.html",
            token=token,
            grupos=grupos,
            nome_restaurante=config.NOME_RESTAURANTE,
            taxa_entrega=config.TAXA_ENTREGA,
            erro="Selecione ao menos um item antes de enviar o pedido.",
        ), 400

    try:
        pedido = pedidos.criar_pedido(
            telefone=telefone,
            nome_cliente=nome_cliente,
            itens=itens,
            forma_pagamento=forma_pagamento,
            forma_entrega=forma_entrega,
            cep=cep,
            endereco=endereco,
        )
    except ValueError as exc:
        produtos = cardapio.listar_produtos_ativos()
        grupos = cardapio.agrupar_por_categoria(produtos)
        return render_template(
            "pedido.html",
            token=token,
            grupos=grupos,
            nome_restaurante=config.NOME_RESTAURANTE,
            taxa_entrega=config.TAXA_ENTREGA,
            erro=str(exc),
        ), 400

    marcar_link_usado(token, pedido["id"])

    mensagem_confirmacao = recibo.montar_mensagem_confirmacao(pedido)
    cupom = recibo.montar_recibo(pedido)
    try:
        whatsapp.enviar_mensagem(telefone, mensagem_confirmacao)
        whatsapp.enviar_mensagem(telefone, cupom)
        pedidos.registrar_mensagem(telefone, "SAIDA", mensagem_confirmacao)
        pedidos.registrar_mensagem(telefone, "SAIDA", cupom)

        mensagem_status = recibo.montar_mensagem_status(pedido, "CONFIRMADO")
        whatsapp.enviar_mensagem(telefone, mensagem_status)
        pedidos.registrar_mensagem(telefone, "SAIDA", mensagem_status)
    except Exception:
        # O pedido já foi salvo com sucesso -- uma falha ao notificar pelo
        # WhatsApp não deve impedir de mostrar a confirmação na tela.
        logger.exception("Pedido %s criado, mas falhou ao notificar %s pelo WhatsApp", pedido["numero_pedido"], telefone)

    return redirect(url_for("recibo_pedido", token=token))


@app.route("/m/<token>/recibo", methods=["GET"])
def recibo_pedido(token):
    """Confirmação do pedido. Fica no próprio sistema, não num arquivo local.
    O link do cardápio continua de uso único; esta página só mostra o recibo."""
    link = obter_link(token)
    if not link or not link.get("usado") or not link.get("pedido_id"):
        return render_template(
            "link_invalido.html",
            mensagem="Este link de pedido não existe ou ainda não foi concluído.",
        ), 410
    pedido = pedidos.obter_pedido(link["pedido_id"])
    if pedido is None:
        return render_template(
            "link_invalido.html",
            mensagem="Não encontrei o pedido deste link.",
        ), 410
    return render_template("pedido_sucesso.html", pedido=pedido)


# ---------------------------------------------------------------------------
# Painel da cozinha / fila de preparo -- protegido por HTTP Basic Auth
# (COZINHA_USUARIO / COZINHA_SENHA no .env). Sem essas variáveis definidas,
# o painel fica bloqueado por padrão.
# ---------------------------------------------------------------------------

@app.route("/cozinha", methods=["GET"])
@requer_login_cozinha
def painel_cozinha():
    return render_template("cozinha.html", fila=fila.listar_fila())


@app.route("/cozinha/avancar/<int:pedido_id>", methods=["POST"])
@requer_login_cozinha
def avancar_pedido(pedido_id):
    try:
        fila.avancar_status(pedido_id)
    except ValueError as e:
        return str(e), 400
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"status": "ok"})
    return redirect(url_for("painel_cozinha"))


@app.route("/cozinha/api/fila", methods=["GET"])
@requer_login_cozinha
def api_fila():
    """Usado pelo JavaScript do painel da cozinha para atualizar a fila sem
    recarregar a página inteira (sem o 'flicker' do refresh completo)."""
    return jsonify(fila.listar_fila())


# ---------------------------------------------------------------------------
# Conectar o WhatsApp (QR Code) -- só abre no próprio notebook
# ---------------------------------------------------------------------------

@app.route("/whatsapp", methods=["GET"])
@apenas_neste_computador
def pagina_whatsapp():
    return render_template("whatsapp.html", nome=config.NOME_RESTAURANTE)


@app.route("/whatsapp/status", methods=["GET"])
@apenas_neste_computador
def whatsapp_status():
    return jsonify(waha_admin.status_sessao())


@app.route("/whatsapp/qr.png", methods=["GET"])
@apenas_neste_computador
def whatsapp_qr():
    png = waha_admin.obter_qr_png()
    if not png:
        return "", 404
    return Response(png, mimetype="image/png", headers={"Cache-Control": "no-store"})


@app.route("/whatsapp/iniciar", methods=["POST"])
@apenas_neste_computador
def whatsapp_iniciar():
    return jsonify({"ok": waha_admin.iniciar_sessao()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=config.FLASK_DEBUG)
