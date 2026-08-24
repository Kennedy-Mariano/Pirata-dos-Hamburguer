-- Entidades mínimas do banco (Tema 09 - DeliveryBot):
-- clientes, produtos, pedidos, itens_pedido, fila_preparo, mensagens

CREATE TABLE IF NOT EXISTS clientes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    telefone      TEXT NOT NULL UNIQUE,      -- número do WhatsApp (com DDI/DDD)
    cep           TEXT,
    endereco      TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS produtos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    categoria     TEXT NOT NULL,             -- lanche, bebida, sobremesa...
    descricao     TEXT,
    preco         REAL NOT NULL,
    ativo         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pedidos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_pedido       TEXT NOT NULL UNIQUE,     -- ex: #21535858, exibido ao cliente
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id),
    origem              TEXT NOT NULL DEFAULT 'Bot Atendimento',
    forma_entrega       TEXT NOT NULL,            -- 'RETIRADA BALCAO' ou 'ENTREGA'
    tempo_estimado_min  INTEGER NOT NULL,
    forma_pagamento     TEXT NOT NULL,
    total_itens         REAL NOT NULL,
    total_pedido        REAL NOT NULL,
    total_pago          REAL NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'RECEBIDO',
    -- RECEBIDO -> CONFIRMADO -> EM_PREPARO -> PRONTO -> ENTREGUE/RETIRADO -> CANCELADO
    criado_em           TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id     INTEGER NOT NULL REFERENCES pedidos(id),
    produto_id    INTEGER NOT NULL REFERENCES produtos(id),
    quantidade    INTEGER NOT NULL,
    preco_unitario REAL NOT NULL,
    observacao    TEXT
);

CREATE TABLE IF NOT EXISTS fila_preparo (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id     INTEGER NOT NULL UNIQUE REFERENCES pedidos(id),
    posicao       INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'AGUARDANDO',
    -- AGUARDANDO -> EM_PREPARO -> PRONTO -> RETIRADO
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mensagens (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone      TEXT NOT NULL,
    direcao       TEXT NOT NULL,           -- 'ENTRADA' (cliente -> bot) ou 'SAIDA' (bot -> cliente)
    conteudo      TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Link único de pedido: cada token só pode gerar UM pedido.
CREATE TABLE IF NOT EXISTS links_pedido (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    token         TEXT NOT NULL UNIQUE,
    telefone      TEXT NOT NULL,
    usado         INTEGER NOT NULL DEFAULT 0,
    pedido_id     INTEGER REFERENCES pedidos(id),
    expira_em     TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Estado da conversa do bot por telefone (menu, aguardando escolha, etc.)
CREATE TABLE IF NOT EXISTS sessoes_bot (
    telefone      TEXT PRIMARY KEY,
    estado        TEXT NOT NULL DEFAULT 'MENU',
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
