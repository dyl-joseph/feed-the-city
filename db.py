import json
import os
import sqlite3
import urllib.request

TURSO_URL = os.environ.get('TURSO_DATABASE_URL', '')
TURSO_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')


class TursoDB:
    def __init__(self):
        self._base_url = TURSO_URL.replace("libsql://", "https://")

    def _request(self, sql, params=()):
        args = []
        for p in params:
            if isinstance(p, int):
                args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                args.append({"type": "float", "value": str(p)})
            elif p is None:
                args.append({"type": "null"})
            else:
                args.append({"type": "text", "value": str(p)})

        body = json.dumps({
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args}},
                {"type": "close"}
            ]
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/v2/pipeline",
            data=body,
            headers={
                "Authorization": f"Bearer {TURSO_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        result = data["results"][0]["response"]["result"]
        return result

    def execute(self, sql, params=()):
        result = self._request(sql, params)
        return _TursoResult(result)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class _TursoResult:
    def __init__(self, result):
        self._result = result
        cols = result.get("cols", [])
        self.description = [(c["name"], None, None, None, None, None, None) for c in cols] if cols else None
        self.lastrowid = result.get("last_insert_rowid")

    @staticmethod
    def _cast(cell):
        t = cell.get("type", "")
        v = cell.get("value")
        if t == "null" or v is None:
            return None
        if t == "integer":
            return int(v)
        if t == "float":
            return float(v)
        return v

    def fetchall(self):
        rows = []
        for row in self._result.get("rows", []):
            rows.append(tuple(self._cast(cell) for cell in row))
        return rows

    def fetchone(self):
        all_rows = self.fetchall()
        return all_rows[0] if all_rows else None


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
