"""Secrets, keys and the gateway database must be rejected by path, without reading them."""
import pytest

from scripts import check


def test_check_rejects_tracked_key_path(tmp_path, monkeypatch, capsys):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/README.md').write_text('')
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    monkeypatch.setattr(check, 'tracked_files', lambda: ['data/keys/demo.pem'])
    assert check.main() == 1
    assert 'data/keys/demo.pem: secret' in capsys.readouterr().out


@pytest.mark.parametrize('path', [
    '.env', '.env.local', '.env.production', 'app/.env.staging', 'certs/server.pem', 'agent.key',
    'vpn/profile.ovpn', 'data/snapshots/a.json', 'data/zeta.db', 'data/zeta.db-wal',
])
def test_check_rejects_secret_paths(tmp_path, monkeypatch, path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/README.md').write_text('')
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    monkeypatch.setattr(check, 'tracked_files', lambda: [path])
    assert check.main() == 1


@pytest.mark.parametrize('path', ['.env.example', 'docs/keys.md', 'zeta_one/db.py'])
def test_check_allows_ordinary_paths(path):
    assert not any(pattern.search(path) for pattern in check.FORBIDDEN)
