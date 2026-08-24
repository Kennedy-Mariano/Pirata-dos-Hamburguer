-- Esquema SQLite para testes rápidos locais
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS produtos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE,
  categoria TEXT,
  custo_unitario NUMERIC DEFAULT 0,
  preco_venda NUMERIC DEFAULT 0,
  quantidade_estoque INTEGER DEFAULT 10,
  estoque_minimo INTEGER DEFAULT 2
);

CREATE TABLE IF NOT EXISTS pedidos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_nome TEXT,
  cliente_telefone TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS itens_pedido (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
  produto_id INTEGER REFERENCES produtos(id),
  quantidade INTEGER,
  preco_unitario NUMERIC,
  custo_unitario NUMERIC
);

CREATE TABLE IF NOT EXISTS single_use_tokens (
  token TEXT PRIMARY KEY,
  pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
  used INTEGER DEFAULT 0 NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP
);

-- Tabela de alertas de reposição (opcional)
CREATE TABLE IF NOT EXISTS alertas_reposicao (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  produto_id INTEGER,
  quantidade_atual INTEGER,
  estoque_minimo INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dados de exemplo
INSERT OR IGNORE INTO produtos (nome, categoria, custo_unitario, preco_venda, quantidade_estoque, estoque_minimo) VALUES
  ('X-Bacon', 'Lanche', 10.00, 25.00, 10, 2),
  ('GUARANA ZERO ACUCAR', 'Bebida', 2.00, 6.00, 20, 2);
