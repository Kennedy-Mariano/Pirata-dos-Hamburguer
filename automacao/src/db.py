"""
Conexão com o banco de dados PostgreSQL.
"""
import psycopg2
import psycopg2.extras
from src import config


def get_connection():
    """Abre e retorna uma conexão com o PostgreSQL."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def buscar_produtos(conn):
    """Busca todos os produtos cadastrados."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nome, categoria, custo_unitario, preco_venda,
                   quantidade_estoque, estoque_minimo
            FROM produtos
            ORDER BY nome;
        """)
        return cur.fetchall()


def buscar_produto_por_nome(conn, nome):
    """Busca um produto pelo nome (usado ao registrar um pedido do WhatsApp)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nome, categoria, custo_unitario, preco_venda,
                   quantidade_estoque, estoque_minimo
            FROM produtos
            WHERE LOWER(nome) = LOWER(%s)
            LIMIT 1;
        """, (nome,))
        return cur.fetchone()


def criar_pedido(conn, cliente_nome, cliente_telefone, itens):
    """
    Cria um pedido e seus itens.
    itens = [{"produto_id": 1, "quantidade": 2}, ...]
    Retorna o id do pedido criado.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO pedidos (cliente_nome, cliente_telefone)
            VALUES (%s, %s) RETURNING id;
        """, (cliente_nome, cliente_telefone))
        pedido_id = cur.fetchone()["id"]

        for item in itens:
            cur.execute("""
                SELECT preco_venda, custo_unitario, quantidade_estoque
                FROM produtos WHERE id = %s;
            """, (item["produto_id"],))
            produto = cur.fetchone()

            cur.execute("""
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, custo_unitario)
                VALUES (%s, %s, %s, %s, %s);
            """, (pedido_id, item["produto_id"], item["quantidade"],
                  produto["preco_venda"], produto["custo_unitario"]))

            # baixa no estoque
            cur.execute("""
                UPDATE produtos SET quantidade_estoque = quantidade_estoque - %s
                WHERE id = %s;
            """, (item["quantidade"], item["produto_id"]))

        conn.commit()
        return pedido_id


def registrar_alerta_reposicao(conn, produto_id, quantidade_atual, estoque_minimo):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alertas_reposicao (produto_id, quantidade_atual, estoque_minimo)
            VALUES (%s, %s, %s);
        """, (produto_id, quantidade_atual, estoque_minimo))
        conn.commit()


def buscar_dados_powerbi(conn):
    """Busca os dados já calculados (receita, custo, lucro) da view usada pelo Power BI."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM vw_powerbi_pedidos ORDER BY data_pedido DESC;")
        return cur.fetchall()
