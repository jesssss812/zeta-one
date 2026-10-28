"""Create local demo signing keys and an admin token; never print credentials."""
import argparse
import os
from pathlib import Path
import re
import secrets
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

DEMO_AGENTS = ('ap_assistant',)

def _write_new(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(content)

def generate(root: Path, agents=DEMO_AGENTS) -> None:
    """Generate only missing keys; preserve existing environment entries and key material."""
    root = Path(root)
    agents = tuple(agents)
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in agents):
        raise ValueError('agent names must contain only letters, digits, underscores and hyphens')
    directory = root / 'data' / 'keys'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in agents:
        path = directory / f'{name}.pem'
        if path.exists():
            continue
        key = Ed25519PrivateKey.generate()
        try:
            _write_new(path, key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        except FileExistsError:
            pass
    environment = root / '.env'
    if not environment.exists():
        try:
            _write_new(environment, f'ZETA_ADMIN_TOKEN={secrets.token_urlsafe(32)}\n'.encode())
            return
        except FileExistsError:
            pass
    content = environment.read_text()
    if re.search(r'^\s*(?:export\s+)?ZETA_ADMIN_TOKEN\s*=', content, flags=re.MULTILINE):
        return
    # Append rather than rewrite: preserve all existing settings byte for byte.
    descriptor = os.open(environment, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'a') as stream:
        stream.write(('' if not content or content.endswith('\n') else '\n') +
                     f'ZETA_ADMIN_TOKEN={secrets.token_urlsafe(32)}\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--agent', action='append', dest='agents')
    args = parser.parse_args()
    generate(args.root, args.agents or DEMO_AGENTS)

if __name__ == '__main__':
    main()
