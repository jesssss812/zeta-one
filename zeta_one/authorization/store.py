"""Versioned, unsigned authorization documents owned by the gateway."""
import sqlite3
from datetime import datetime
from zeta_one.contracts import Authorization, AuthorizationSource

class Store:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        connection.execute('''CREATE TABLE IF NOT EXISTS authorization_documents (
          business_id TEXT NOT NULL, agent_id TEXT NOT NULL, authorization_id TEXT NOT NULL,
          version INTEGER NOT NULL, document TEXT NOT NULL,
          PRIMARY KEY(business_id, agent_id, version))''')
        connection.commit()

    def grant(self, authorization: Authorization) -> Authorization:
        with self.connection:
            latest = self.connection.execute(
                'SELECT MAX(version) FROM authorization_documents WHERE business_id=? AND agent_id=?',
                (authorization.business_id, authorization.agent_id)).fetchone()[0]
            if latest is not None and authorization.version <= latest:
                raise ValueError('authorization version must increase')
            if authorization.status != 'active' or authorization.revoked_at is not None:
                raise ValueError('a grant must be active')
            self.connection.execute('INSERT INTO authorization_documents VALUES (?, ?, ?, ?, ?)',
                (authorization.business_id, authorization.agent_id, authorization.authorization_id,
                 authorization.version, authorization.model_dump_json()))
        return authorization

    def revoke(self, authorization_id: str, now: datetime) -> None:
        with self.connection:
            rows = self.connection.execute('''SELECT business_id, agent_id, version, document
                FROM authorization_documents WHERE authorization_id=? AND version=(
                  SELECT MAX(b.version) FROM authorization_documents b WHERE
                  b.business_id=authorization_documents.business_id AND b.agent_id=authorization_documents.agent_id)''',
                (authorization_id,)).fetchall()
            for business, agent, version, document in rows:
                authorization = Authorization.model_validate_json(document)
                authorization.status, authorization.revoked_at = 'revoked', now
                self.connection.execute('UPDATE authorization_documents SET document=? WHERE business_id=? AND agent_id=? AND version=?',
                                        (authorization.model_dump_json(), business, agent, version))

    def load(self, business_id: str, agent_id: str) -> Authorization | None:
        row = self.connection.execute('''SELECT document FROM authorization_documents
            WHERE business_id=? AND agent_id=? ORDER BY version DESC LIMIT 1''', (business_id, agent_id)).fetchone()
        return Authorization.model_validate_json(row[0]) if row else None

    def loader(self) -> AuthorizationSource:
        return self.load
