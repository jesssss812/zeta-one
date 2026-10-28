"""Key generation is tested only in temporary directories."""
import stat
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from scripts.keygen import generate

def test_keygen_is_private_and_idempotent(tmp_path, capsys):
    generate(tmp_path, ['demo'])
    key_path = tmp_path / 'data/keys/demo.pem'
    original = key_path.read_bytes()
    load_pem_private_key(original, password=None)
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    environment = tmp_path / '.env'
    first = environment.read_bytes()
    assert first.startswith(b'ZETA_ADMIN_TOKEN=')
    generate(tmp_path, ['demo'])
    assert key_path.read_bytes() == original
    assert environment.read_bytes() == first
    assert capsys.readouterr().out == ''

def test_existing_environment_preserved(tmp_path):
    environment = tmp_path / '.env'
    environment.write_text('UNRELATED=synthetic\nZETA_ADMIN_TOKEN=synthetic-test-only\n')
    original = environment.read_bytes()
    generate(tmp_path, ['demo'])
    assert environment.read_bytes() == original
