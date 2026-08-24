"""
Conexão com o banco de dados SQLite para o módulo automacao (mirror do src/db.py).
"""
import sqlite3
from pathlib import Path
from src import config

DB_PATH = getattr(config, "DB_PATH", None) or str(Path(config.PASTA_DADOS) / "app.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def buscar_produtos(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nome, categoria, custo_unitario, preco_venda, quantidade_estoque, estoque_minimo FROM produtos ORDER BY nome;"
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def buscar_produto_por_nome(conn, nome):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nome, categoria, custo_unitario, preco_venda, quantidade_estoque, estoque_minimo FROM produtos WHERE LOWER(nome) = LOWER(?) LIMIT 1;",
        (nome,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def criar_pedido(conn, cliente_nome, cliente_telefone, itens):
    cur = conn.cursor()
    cur.execute("INSERT INTO pedidos (cliente_nome, cliente_telefone) VALUES (?, ?);", (cliente_nome, cliente_telefone))
    pedido_id = cur.lastrowid
    for item in itens:
        cur.execute("SELECT preco_venda, custo_unitario, quantidade_estoque FROM produtos WHERE id = ?;", (item["produto_id"],))
        produto = cur.fetchone()
        if not produto:
            continue
        preco_venda = float(produto["preco_venda"]) if produto["preco_venda"] is not None else 0.0
        custo_unitario = float(produto["custo_unitario"]) if produto["custo_unitario"] is not None else 0.0
        cur.execute("INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, custo_unitario) VALUES (?, ?, ?, ?, ?);", (pedido_id, item["produto_id"], item["quantidade"], preco_venda, custo_unitario))
        cur.execute("UPDATE produtos SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?;", (item["quantidade"], item["produto_id"]))
    conn.commit()
    return pedido_id


def registrar_alerta_reposicao(conn, produto_id, quantidade_atual, estoque_minimo):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS alertas_reposicao (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, quantidade_atual INTEGER, estoque_minimo INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    cur.execute("INSERT INTO alertas_reposicao (produto_id, quantidade_atual, estoque_minimo) VALUES (?, ?, ?);", (produto_id, quantidade_atual, estoque_minimo))
    conn.commit()


def buscar_dados_powerbi(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT p.id as pedido_id, pr.nome as produto, ip.quantidade as quantidade, ip.preco_unitario as receita, ip.custo_unitario as custo_total, (ip.preco_unitario - ip.custo_unitario) * ip.quantidade as lucro, p.created_at as data_pedido FROM itens_pedido ip JOIN produtos pr ON pr.id = ip.produto_id JOIN pedidos p ON p.id = ip.pedido_id ORDER BY data_pedido DESC;"
    )
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "pedido_id": int(r["pedido_id"]),
            "produto": r["produto"],
            "quantidade": int(r["quantidade"]),
            "receita": float(r["receita"]),
            "custo_total": float(r["custo_total"]),
            "lucro": float(r["lucro"]),
            "data_pedido": r["data_pedido"],
        })
    return out
