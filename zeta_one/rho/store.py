"""An isolated, synthetic Rho stand-in in SQLite; never accesses live Rho or snapshots.

Rho entities retain their API shape. Business ownership, method timestamps/history, payment
destinations and bill text are local stand-in records, since Rho's records as staging shows them
don't carry them. All table names are prefixed rho_.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

from zeta_one.rho.models import Account, Bill, Business, Counterparty, Transaction

SEED_DIR = Path(__file__).resolve().parents[2] / 'data' / 'seed'
MODELS = {'businesses':Business, 'accounts':Account, 'counterparties':Counterparty,
          'bills':Bill, 'transactions':Transaction}
TABLES = (*MODELS, 'ownership', 'method_dates', 'method_history', 'payment_destinations', 'bill_text')


class Store:
    def __init__(self, seed_dir: str | Path = SEED_DIR):
        self.connection = sqlite3.connect(':memory:', check_same_thread=False)
        self.connection.execute('PRAGMA foreign_keys = ON')
        for table in TABLES:
            self.connection.execute(f'CREATE TABLE rho_{table} (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        seed_dir = Path(seed_dir)
        digest = hashlib.sha256()
        for path in sorted(seed_dir.rglob('*')):
            if path.is_file():
                name = path.relative_to(seed_dir).as_posix().encode()
                content = path.read_bytes()
                digest.update(len(name).to_bytes(8, 'big') + name)
                digest.update(len(content).to_bytes(8, 'big') + content)
        self.seed_version = digest.hexdigest()
        for table in TABLES:
            for record in json.loads((seed_dir / f'{table}.json').read_text()):
                self.put(table, record)

    def put(self, table: str, record: dict):
        self._table(table)
        if table in MODELS:
            record = MODELS[table].model_validate(record).model_dump(mode='json')
        self.connection.execute(f'INSERT INTO rho_{table} VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                                (record['id'], json.dumps(record)))
        self.connection.commit()

    def get(self, table: str, record_id: str) -> dict | None:
        self._table(table)
        row = self.connection.execute(f'SELECT data FROM rho_{table} WHERE id=?', (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, table: str) -> list[dict]:
        self._table(table)
        return [json.loads(row[0]) for row in self.connection.execute(f'SELECT data FROM rho_{table} ORDER BY rowid')]

    def _table(self, table):
        if table not in TABLES:
            raise ValueError('Unknown stand-in table')

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
