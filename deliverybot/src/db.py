import json
import os
import sqlite3
from contextlib import contextmanager

from . import config

_SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql")
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _connect():
    os.makedirs(os.path.dirname(config.DATABASE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(seed_cardapio: bool = True):
    """Cria as tabelas (se não existirem) e popula o cardápio inicial."""
    schema_path = os.path.join(_SQL_DIR, "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()

    with get_conn() as conn:
        conn.executescript(schema_sql)

        if seed_cardapio:
            existing = conn.execute("SELECT COUNT(*) AS n FROM produtos").fetchone()["n"]
            if existing == 0:
                cardapio_path = os.path.join(_DATA_DIR, "cardapio.json")
                with open(cardapio_path, encoding="utf-8") as f:
                    itens = json.load(f)
                for item in itens:
                    conn.execute(
                        "INSERT INTO produtos (nome, categoria, descricao, preco, ativo) "
                        "VALUES (?, ?, ?, ?, 1)",
                        (item["nome"], item["categoria"], item.get("descricao", ""), item["preco"]),
                    )
    return True
