# Automação de Estoque + Pedidos via WhatsApp + Power BI

![Testes](https://github.com/Kennedy-Mariano/Pirata-dos-Hamburguer/actions/workflows/tests.yml/badge.svg)
Figma:https://www.figma.com/design/Dx1ooiJuJjY7cJ0QP9GfW0/Untitled?node-id=0-1&m=dev&t=OgGVHb60ZdnKJ5Uk-1
## Integrantes do grupo
| Nº | Nome completo | Função no grupo |
|----|----------------|------------------|
| 1  | Cleryton Kaique Chagas | Dono do projeto |
| 2  | Kennedy Mariano Kulibaba Peruzzolo | Desenvolvimento / Front-end / Protótipo no Figma |
| 3  | Gabriel Bieliek | Colaborador |

## Resumo da automação proposta
Este projeto automatiza o ciclo completo de um pequeno negócio que vende
produtos e recebe pedidos pelo **WhatsApp**. O sistema:
1. Recebe pedidos automaticamente pelo **WhatsApp**;
2. Conecta ao **PostgreSQL**, dá baixa no estoque e verifica reposição;
3. Calcula **custo efetivo, receita e lucro** de cada pedido;
4. Atualiza os dados usados no **Power BI**;
5. Gera um **relatório em PDF** e envia por **e-mail** ao responsável;
6. Envia uma **confirmação automática** ao cliente pelo WhatsApp.

Com isso, o dono do negócio deixa de controlar estoque e lucro manualmente
em planilhas e passa a ter tudo automatizado e visível em um painel do Power BI.
Este projeto implementa exatamente o fluxo descrito no documento da Entrega 1
(itens 7 e 10 — Como Funcionará a Automação / Fluxograma).

## Tecnologias e ferramentas utilizadas
| Tecnologia | Uso no projeto |
|---|---|
| **Python 3** | Linguagem principal da automação |
| **PostgreSQL** | Banco de dados de produtos, estoque, pedidos e custos |
| **Flask** | Servidor do webhook que recebe os pedidos do WhatsApp |
| **WhatsApp Business Cloud API (Meta)** | Recebimento e envio automático de mensagens |
| **ReportLab** | Geração automática do relatório em PDF |
| **smtplib (E-mail/SMTP)** | Envio automático do relatório por e-mail |
| **Pandas** | Tratamento dos dados de custo, receita e lucro |
| **Power BI** | Painel visual com indicadores de estoque, vendas e lucratividade |
| **Docker / docker-compose** | Sobe um PostgreSQL local para testes |
| **schedule** | Execução automática e periódica da rotina |

---

## 1. Estrutura de pastas

```
automacao/
├── .github/workflows/tests.yml -> roda os testes automaticamente no GitHub Actions
├── docker-compose.yml       -> sobe um PostgreSQL local para testes
├── requirements.txt
├── requirements-dev.txt     -> requirements.txt + pytest (para rodar os testes)
├── .env.example             -> copie para .env e preencha suas credenciais
├── .gitignore                -> ignora .env, venv, __pycache__ e saídas geradas
├── tests/                     -> testes automatizados (pytest)
├── sql/
│   ├── schema.sql            -> cria as tabelas e a view usada pelo Power BI
│   └── seed.sql               -> produtos de exemplo
├── src/
│   ├── config.py              -> lê as variáveis do .env
│   ├── db.py                  -> conexão e consultas no PostgreSQL
│   ├── estoque.py             -> regra de comparação com o estoque mínimo
│   ├── financeiro.py          -> cálculo de custo, receita e lucro
│   ├── whatsapp.py            -> integração com a API do WhatsApp Business
│   ├── relatorio.py           -> geração do PDF
│   ├── email_sender.py        -> envio do relatório por e-mail
│   ├── powerbi_export.py      -> exporta CSV e/ou envia para um streaming dataset
│   ├── pipeline.py            -> orquestra todo o fluxo (chamado pelo app.py e main.py)
│   ├── app.py                 -> servidor Flask (webhook do WhatsApp, tempo real)
│   └── main.py                -> execução manual/agendada (sem depender do webhook)
├── data/                      -> aqui é salvo o dados_powerbi.csv
└── relatorios/                -> aqui são salvos os PDFs gerados
```

## 2. Passo a passo para rodar

### 2.1. Instalar as dependências
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2. Subir o banco de dados PostgreSQL
Se tiver Docker instalado:
```bash
docker compose up -d
```
Isso já cria as tabelas (`schema.sql`) e os produtos de exemplo (`seed.sql`) automaticamente.

Se preferir usar um PostgreSQL já existente, apenas rode os dois arquivos SQL manualmente:
```bash
psql -h localhost -U seu_usuario -d seu_banco -f sql/schema.sql
psql -h localhost -U seu_usuario -d seu_banco -f sql/seed.sql
```

### 2.3. Configurar as variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` com:
- Dados do banco (se não usar o `docker-compose.yml` padrão);
- Token e ID do número do **WhatsApp Business Cloud API** (obtidos no [Meta for Developers](https://developers.facebook.com/));
- Usuário/senha de app do e-mail que vai enviar o relatório;
- URL do streaming dataset do Power BI (opcional).

> **Modo teste:** se você não preencher o WhatsApp, e-mail ou Power BI no `.env`, o
> sistema não quebra — ele apenas imprime no console o que faria ("[MODO TESTE]"),
> o que é ótimo para testar a lógica sem ter as credenciais ainda.

### 2.4. Rodar a automação manualmente
```bash
python -m src.main
```
Isso executa uma vez: verifica reposição de estoque, calcula lucro, exporta os
dados para o Power BI, gera o PDF e tenta enviar o e-mail.

Para deixar rodando e executar automaticamente todo dia às 18h:
```bash
python -m src.main --agendar
```

### 2.5. Rodar o webhook para receber pedidos reais do WhatsApp
```bash
python -m src.app
```
Em desenvolvimento, exponha a porta 5000 publicamente (ex.: `ngrok http 5000`) e
cadastre a URL + o `WHATSAPP_VERIFY_TOKEN` no painel de Webhooks da Meta.

Formato de pedido que o cliente envia pelo WhatsApp:
```
PEDIDO: 2x Camiseta Basica Branca, 1x Caneca Personalizada
```

## 3. Conectando ao Power BI

Duas formas, conforme explicado em `src/powerbi_export.py`:

- **Simples (arquivo):** o sistema gera `data/dados_powerbi.csv` a cada execução.
  No Power BI Desktop: `Obter Dados > Texto/CSV` e aponte para esse arquivo.
  Configure a atualização automática (via Gateway) se quiser dados sempre atualizados.

- **Tempo real (streaming dataset):** crie um *Streaming dataset* no Power BI
  Service (com as colunas: pedido_id, produto, quantidade, receita, custo_total,
  lucro, data_pedido), copie a **Push URL** gerada e cole em `POWERBI_PUSH_URL`
  no `.env`. A cada pedido processado, os dados são enviados automaticamente.

## 4. Fluxo completo (resumo)

```
Cliente manda pedido no WhatsApp
        ↓
Webhook recebe e interpreta o pedido
        ↓
Conecta ao PostgreSQL e registra o pedido (baixa automática no estoque)
        ↓
Compara estoque atual x estoque mínimo → gera alerta se necessário
        ↓
Calcula custo efetivo, receita e lucro do pedido
        ↓
Atualiza a base usada pelo Power BI (CSV e/ou streaming dataset)
        ↓
Gera relatório em PDF (reposição + resumo financeiro + vendas)
        ↓
Envia o relatório por e-mail ao responsável
        ↓
Envia confirmação automática do pedido ao cliente pelo WhatsApp
```

## 5. Testes automatizados

O projeto tem uma suíte de testes (`pytest`) que cobre as regras de negócio
principais **sem precisar de credenciais reais de WhatsApp/e-mail/Power BI**
(elas rodam em "modo teste" automaticamente quando o `.env` não está preenchido):

- `tests/test_estoque.py` — regra de reposição de estoque;
- `tests/test_financeiro.py` — cálculo de receita, custo, lucro e margem;
- `tests/test_whatsapp.py` — interpretação das mensagens e do payload do webhook;
- `tests/test_powerbi_relatorio.py` — exportação do CSV do Power BI e geração do PDF.

O único pré-requisito é um PostgreSQL configurado (via `docker compose up -d` ou
uma instância própria, com `schema.sql` e `seed.sql` aplicados) para os testes
manuais de ponta a ponta do pipeline completo — os testes automatizados acima
não tocam no banco.

```bash
pip install -r requirements-dev.txt
pytest -v
```

Os testes também rodam automaticamente a cada `push`/Pull Request via GitHub
Actions (veja `.github/workflows/tests.yml` e o badge no topo deste README).

### Teste manual de ponta a ponta (opcional)
Depois de subir o banco (`docker compose up -d`) e copiar o `.env.example`
para `.env`, é possível simular um pedido completo sem precisar do WhatsApp real:

```bash
python -c "
from src.pipeline import processar_pedido
print(processar_pedido('Cliente Teste', '5541999999999', [
    {'nome_produto': 'Camiseta Basica Branca', 'quantidade': 2},
]))
"
```
Isso cria o pedido, baixa o estoque, calcula o lucro, gera `data/dados_powerbi.csv`
e um PDF em `relatorios/`, e imprime no console a mensagem que seria enviada ao
cliente (modo teste, já que não há credenciais do WhatsApp configuradas).

## 6. Próximos passos sugeridos
- Trocar o parser de texto simples do WhatsApp por um menu com botões/listas interativas;
- Adicionar autenticação/usuários no relatório;
- Criar uma tela web simples para cadastro de produtos (hoje é feito direto no banco);
- Adicionar testes automatizados (pytest) para as regras de estoque e financeiro.
- Adicionar testes automatizados (pytest) para as regras de estoque e financeiro.
<<<<<<< HEAD
=======
- Adicionar testes automatizados (pytest) para as regras de estoque e financeiro.
