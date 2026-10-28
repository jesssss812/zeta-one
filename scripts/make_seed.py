"""Regenerate the deterministic synthetic seed. No network or credentials are used."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from zeta_one.rho.seed import make_seed
from zeta_one.rho.store import SEED_DIR

if __name__ == '__main__':
    make_seed(SEED_DIR)
    print('Wrote synthetic seed; all execution is simulated.')
