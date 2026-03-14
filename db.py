import os
import libsql_experimental as libsql

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '')
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')

def get_db():
    if TURSO_URL:
        conn = libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'feed_the_city.db')
        conn = libsql.connect(database=db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql')) as f:
        for statement in f.read().split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        conn.commit()
    conn.close()
