import os
import sqlite3

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '')
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')


def get_db():
    if TURSO_URL:
        import libsql_experimental as libsql
        url = TURSO_URL.replace("libsql://", "https://")
        conn = libsql.connect(url, auth_token=TURSO_TOKEN)
        return conn
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'feed_the_city.db'))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    conn = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path) as f:
        for statement in f.read().split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
    conn.commit()
    conn.close()
