"""Conexão do WhatsApp pelo WAHA, feita para leigos.

Em vez de obrigar a pessoa a entrar no dashboard do WAHA (usuário, senha,
chave de API...), o Flask mostra uma página simples em /whatsapp com o QR
Code e o status da conexão. A chave de API do WAHA fica só aqui no servidor
-- nunca vai para o navegador.
"""
import base64
import logging

import requests

from . import config

logger = logging.getLogger(__name__)


def _headers(accept: str | None = None) -> dict:
    h = {}
    if config.WAHA_API_KEY:
        h["X-Api-Key"] = config.WAHA_API_KEY
    if accept:
        h["Accept"] = accept
    return h


def _url(caminho: str) -> str:
    return f"{config.WAHA_URL}{caminho}"


def status_sessao() -> dict:
    """Retorna {"status": <STOPPED|STARTING|SCAN_QR_CODE|WORKING|FAILED|
    INDISPONIVEL|SEM_SESSAO>, "numero": <str|None>}."""
    try:
        r = requests.get(
            _url(f"/api/sessions/{config.WAHA_SESSION}"), headers=_headers(), timeout=5
        )
    except requests.RequestException:
        return {"status": "INDISPONIVEL", "numero": None}

    if r.status_code == 404:
        return {"status": "SEM_SESSAO", "numero": None}
    if r.status_code in (401, 403):
        return {"status": "CHAVE_INVALIDA", "numero": None}
    if not r.ok:
        return {"status": "INDISPONIVEL", "numero": None}

    dados = r.json() or {}
    me = dados.get("me") or {}
    numero = (me.get("id") or "").split("@")[0] or None
    return {"status": dados.get("status", "INDISPONIVEL"), "numero": numero}


def iniciar_sessao() -> bool:
    """Cria/inicia a sessão se ela estiver parada, falha ou inexistente."""
    atual = status_sessao()["status"]
    if atual in ("WORKING", "STARTING", "SCAN_QR_CODE"):
        return True

    nome = config.WAHA_SESSION
    try:
        if atual == "SEM_SESSAO":
            r = requests.post(
                _url("/api/sessions"),
                json={"name": nome, "start": True},
                headers=_headers(),
                timeout=15,
            )
        else:
            if atual == "FAILED":
                requests.post(
                    _url(f"/api/sessions/{nome}/stop"), headers=_headers(), timeout=15
                )
            r = requests.post(
                _url(f"/api/sessions/{nome}/start"), headers=_headers(), timeout=15
            )
        return r.ok
    except requests.RequestException:
        logger.warning("Não consegui iniciar a sessão do WAHA", exc_info=True)
        return False


def obter_qr_png() -> bytes | None:
    """Baixa o QR Code atual (PNG). None se ainda não houver QR."""
    try:
        r = requests.get(
            _url(f"/api/{config.WAHA_SESSION}/auth/qr"),
            headers=_headers("application/json"),
            timeout=10,
        )
    except requests.RequestException:
        return None
    if not r.ok:
        return None

    tipo = r.headers.get("Content-Type", "")
    if tipo.startswith("image/"):
        return r.content
    try:
        dados = r.json().get("data")
        return base64.b64decode(dados) if dados else None
    except (ValueError, AttributeError):
        return None
