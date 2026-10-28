"""Persistent agent public keys and replay protection."""
import sqlite3
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel

class Agent(BaseModel):
    agent_id: str
    business_id: str
    owner: str
    public_key: bytes
    status: str
    created_at: str
    revoked_at: str | None = None

class Registry:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        connection.executescript('''
        CREATE TABLE IF NOT EXISTS identity_agents (
          agent_id TEXT PRIMARY KEY, business_id TEXT NOT NULL, owner TEXT NOT NULL,
          public_key BLOB NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS identity_nonces (
          agent_id TEXT NOT NULL, nonce TEXT NOT NULL, expires_at REAL NOT NULL,
          PRIMARY KEY(agent_id, nonce));
        ''')

    def register(self, agent_id: str, business_id: str, owner: str,
                 public_key: Ed25519PublicKey | bytes, now: datetime) -> Agent:
        raw = public_key.public_bytes_raw() if isinstance(public_key, Ed25519PublicKey) else public_key
        Ed25519PublicKey.from_public_bytes(raw)
        with self.connection:
            self.connection.execute('INSERT INTO identity_agents VALUES (?, ?, ?, ?, ?, ?, NULL)',
                                    (agent_id, business_id, owner, raw, 'active', now.isoformat()))
        return self.get(agent_id)

    def get(self, agent_id: str) -> Agent | None:
        cursor = self.connection.execute('SELECT * FROM identity_agents WHERE agent_id=?', (agent_id,))
        row = cursor.fetchone()
        return Agent(**dict(zip([column[0] for column in cursor.description], row))) if row else None

    def revoke(self, agent_id: str, now: datetime) -> None:
        with self.connection:
            self.connection.execute("UPDATE identity_agents SET status='revoked', revoked_at=? WHERE agent_id=?",
                                    (now.isoformat(), agent_id))

    def seen(self, agent_id: str, nonce: str, now: datetime) -> bool:
        return self.connection.execute('SELECT 1 FROM identity_nonces WHERE agent_id=? AND nonce=? AND expires_at>=?',
                                       (agent_id, nonce, now.timestamp())).fetchone() is not None

    def record_nonce(self, agent_id: str, nonce: str, expires_at: datetime, now: datetime) -> bool:
        with self.connection:
            self.connection.execute('DELETE FROM identity_nonces WHERE expires_at<?', (now.timestamp(),))
            cursor = self.connection.execute('INSERT OR IGNORE INTO identity_nonces VALUES (?, ?, ?)',
                                             (agent_id, nonce, expires_at.timestamp()))
            return cursor.rowcount == 1
