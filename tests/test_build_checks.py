"""Tracked local signing keys must be rejected without inspecting their contents."""
from scripts import check


def test_check_rejects_tracked_key_path(tmp_path, monkeypatch, capsys):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/README.md').write_text('')
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    monkeypatch.setattr(check, 'tracked_files', lambda: ['data/keys/demo.pem'])
    assert check.main() == 1
    assert 'data/keys/demo.pem: secret' in capsys.readouterr().out
