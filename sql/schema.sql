-- Schema do banco de dados PostgreSQL
-- Sistema de Automação de Estoque + Pedidos WhatsApp + Power BI

CREATE TABLE IF NOT EXISTS produtos (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    categoria       VARCHAR(80),
    custo_unitario  NUMERIC(10,2) NOT NULL,     -- quanto custa comprar/produzir 1 unidade
    preco_venda     NUMERIC(10,2) NOT NULL,     -- preço cobrado do cliente
    quantidade_estoque INTEGER NOT NULL DEFAULT 0,
    estoque_minimo  INTEGER NOT NULL DEFAULT 5,
    criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pedidos (
    id              SERIAL PRIMARY KEY,
    cliente_nome    VARCHAR(150) NOT NULL,
    cliente_telefone VARCHAR(30) NOT NULL,      -- número do WhatsApp (com DDI/DDD)
    origem          VARCHAR(30) DEFAULT 'whatsapp',
    status          VARCHAR(30) DEFAULT 'recebido', -- recebido | confirmado | enviado | cancelado
    data_pedido     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id              SERIAL PRIMARY KEY,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id      INTEGER NOT NULL REFERENCES produtos(id),
    quantidade      INTEGER NOT NULL,
    preco_unitario  NUMERIC(10,2) NOT NULL,     -- "foto" do preço no momento da venda
    custo_unitario  NUMERIC(10,2) NOT NULL      -- "foto" do custo no momento da venda
);

CREATE TABLE IF NOT EXISTS alertas_reposicao (
    id              SERIAL PRIMARY KEY,
    produto_id      INTEGER NOT NULL REFERENCES produtos(id),
    quantidade_atual INTEGER NOT NULL,
    estoque_minimo  INTEGER NOT NULL,
    data_alerta     TIMESTAMP NOT NULL DEFAULT NOW(),
    resolvido       BOOLEAN DEFAULT FALSE
);

-- View usada para alimentar o Power BI (custos, receita e lucro por pedido)
CREATE OR REPLACE VIEW vw_powerbi_pedidos AS
SELECT
    pe.id                AS pedido_id,
    pe.data_pedido,
    pe.cliente_nome,
    pe.status,
    pr.nome              AS produto,
    pr.categoria,
    ip.quantidade,
    ip.preco_unitario,
    ip.custo_unitario,
    (ip.quantidade * ip.preco_unitario)                       AS receita,
    (ip.quantidade * ip.custo_unitario)                       AS custo_total,
    (ip.quantidade * (ip.preco_unitario - ip.custo_unitario)) AS lucro
FROM pedidos pe
JOIN itens_pedido ip ON ip.pedido_id = pe.id
JOIN produtos pr     ON pr.id = ip.produto_id;
