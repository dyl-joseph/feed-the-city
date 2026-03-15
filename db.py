import os
import sqlite3

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '')
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')


class TursoDB:
    """Wraps libsql_client to match sqlite3 cursor interface used by query()."""
    def __init__(self):
        from libsql_client import create_client_sync
        url = TURSO_URL.replace("libsql://", "https://")
        self._client = create_client_sync(url=url, auth_token=TURSO_TOKEN)

    def execute(self, sql, params=()):
        rs = self._client.execute(sql, list(params))
        return _TursoResult(rs)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self._client.close()


class _TursoResult:
    """Adapts libsql_client ResultSet to look like a sqlite3 cursor."""
    def __init__(self, rs):
        self._rs = rs
        self.description = [(col, None, None, None, None, None, None) for col in rs.columns] if rs.columns else None
        self.lastrowid = rs.last_insert_rowid

    def fetchall(self):
        return self._rs.rows

    def fetchone(self):
        return self._rs.rows[0] if self._rs.rows else None


def get_db():
    if TURSO_URL:
        return TursoDB()
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'feed_the_city.db'))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path) as f:
        for statement in f.read().split(';'):
            statement = statement.strip()
            if statement:
                db.execute(statement)
    db.commit()
    db.close()
