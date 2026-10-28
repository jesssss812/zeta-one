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


# Built at run time so this file never holds the shapes it tests.
SHAPES = [
    "sk-" + "ant-" + "a" * 30,
    "Authorization: " + "Bearer " + "b" * 40,
    "-----BEGIN " + "PRIVATE KEY-----",
    "RHO_API_TOKEN" + "=" + "c" * 24,
]


@pytest.mark.parametrize('text', SHAPES)
def test_check_refuses_tracked_text_shaped_like_a_credential(tmp_path, monkeypatch, capsys, text):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/README.md').write_text('')
    (tmp_path / 'notes.md').write_text(f"here: {text}\n")
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    monkeypatch.setattr(check, 'tracked_files', lambda: ['notes.md'])
    assert check.main() == 1
    out = capsys.readouterr().out
    assert 'shaped like a credential' in out and text not in out


@pytest.mark.parametrize('text', ["Bearer test-admin-token", "RHO_API_TOKEN in .env", "ZETA_ADMIN_TOKEN=", "sk-ant-..."])
def test_check_allows_ordinary_mentions(text):
    assert not any(pattern.search(text) for pattern in check.SECRET_TEXT)


def test_the_live_rho_client_sends_only_get():
    """Rule 1: the staging check's only request is a GET; any other method in it is a failure."""
    import ast

    source = (check.ROOT / 'scripts' / 'staging_check.py').read_text()
    methods = [kw.value.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
               for kw in node.keywords if kw.arg == 'method' and isinstance(kw.value, ast.Constant)]
    assert methods == ['GET']
    assert 'data=' not in source.replace('metadata=', '')
