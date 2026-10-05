# Relatório de andamento — Pirata dos Hambúrguer / DeliveryBot

Repositório: https://github.com/Kennedy-Mariano/Pirata-dos-Hamburguer

Versões comparadas: branch main e tag deliverybot-v1.0 (commit c8e5b15, 05/10/2026).

Integrantes: Cleryton Kaique Chagas, Kennedy Mariano Kulibaba Peruzzolo e Gabriel Bieliek.

Aprovação: tag deliverybot-v1.0 aprovada por Kennedy em 05/10/2026. O fluxo de pedido foi executado em modo teste (menu, link único, cupom e aviso de status). Seis testes passaram. O teste da fila falha se o WhatsApp estiver em WAHA e o Docker não estiver no ar, porque tenta falar com localhost:3000.

## 1. Situação atual

A main e a tag são dois estados diferentes. A tag tem histórico próprio (sem commit pai), SQLite e WhatsApp via WAHA. A main antiga cobre estoque, lucro, Power BI e PDF em PostgreSQL. Não dá para merge direto.

A v1.0 está mais avançada no atendimento. A main está mais avançada em gestão. As duas ainda não foram unificadas.

A release da tag está publicada: https://github.com/Kennedy-Mariano/Pirata-dos-Hamburguer/releases/tag/deliverybot-v1.0

O bot não é hospedado no GitHub. Roda numa VPS ou num PC com ngrok. O GitHub guarda o código, a release e o workflow de testes.

## 2. O que a tag já tem

- WhatsApp via WAHA (Docker + QR), modo TESTE e opção Meta.
- Atendimento com IA (Ollama ou Anthropic). Sem IA, cai no menu fixo.
- Cardápio em data/cardapio.json e link único /m/<token> (30 min).
- Páginas de pedido, sucesso, link inválido e painel /cozinha com login.
- Fila, recibo e CEP via ViaCEP.
- Taxa, raio, tempo de preparo e horário.
- Fluxo n8n em n8n/deliverybot-waha.json.
- Segredo de webhook, limite de taxa, senha da cozinha, FLASK_DEBUG desligado e gerar_segredos.py.
- iniciar.ps1, .bat e MANUAL.md.
- tests/test_pedidos.py.

## 3. O que ainda falta

Da main, não entrou na v1.0: estoque, custo/lucro, Power BI e PDF por e-mail.

O GitHub Actions de testes está na main, não na tag. O commit 13dd8d (`.github/workflows/tests.yml`) roda pytest só em `deliverybot/tests`, com `WHATSAPP_PROVIDER=TESTE` e sem chamar WhatsApp.

Para fechar o projeto: unificar o código, ligar o Figma nas telas, ampliar testes, definir pagamento se for escopo, validar pedido real e cadastro de produto por tela.

## 4. Problemas fechados nesta revisão

- README da main tinha a linha solta "athumalaka" antes da seção de testes. Removida.
- A release da tag deliverybot-v1.0 foi publicada. A tag sozinha não gerava notas.
- O workflow `jekyll-gh-pages.yml` (commit d48c740) publicava o repositório no GitHub Pages. Foi removido e o Pages foi desligado. O DeliveryBot não é site estático.
- Nomes seguem inconsistentes de propósito nesta versão: repositório Pirata dos Hambúrguer, exemplo Barbaros Lanches.

## 5. Próxima etapa

1. Unificar numa branch, com SQLite no MVP.
2. Trazer estoque, lucro e Power BI da main para o pedidos.py.
3. Integrar o Figma.

## 6. Papéis

- Cleryton: dono. WAHA, IA, n8n e escopo.
- Kennedy: telas, Figma, README e GitHub. Esta aprovação é dele.
- Gabriel: testes, CI e módulo de lucro/estoque.
