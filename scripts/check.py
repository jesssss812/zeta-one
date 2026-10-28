"""Fast checks that must pass before anything is pushed to main.

- Every tracked Python file compiles.
- No secret or raw staging file is tracked, by path, and no tracked text holds something shaped like
  a credential (an API key, a long bearer token, a private key, a filled-in token variable).
- Every relative link in a tracked Markdown file resolves.
- Every file under docs/ is listed in docs/README.md.
- The test suite passes (needs the virtualenv: see README or AGENTS.md).

Usage: python3 scripts/check.py   (exit code 1 on any failure)
"""

import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
FORBIDDEN = (re.compile(r"(^|/)\.env(\.(?!example$)[^/]+)?$"), re.compile(r"\.(ovpn|pem|key|p12)$"),
             re.compile(r"^data/(snapshots|keys)/"), re.compile(r"(^|/)zeta\.db(-wal|-shm|-journal)?$"))
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
SECRET_TEXT = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer [A-Za-z0-9._~+/=-]{32,}"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:RHO_API_TOKEN|ANTHROPIC_API_KEY|ZETA_ADMIN_TOKEN)\s*=\s*['\"]?[A-Za-z0-9._~+/=-]{16,}"),
)
TEXT_SUFFIXES = (".py", ".md", ".json", ".jsonl", ".toml", ".txt", ".yml", ".yaml", ".html", ".js", ".css", ".sh", ".cfg")


def tracked_files():
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [path for path in output.splitlines() if (ROOT / path).exists()]


def main():
    files = tracked_files()
    failures = []

    for path in files:
        if any(pattern.search(path) for pattern in FORBIDDEN):
            failures.append(f"{path}: secret or raw staging file must not be committed")

    for path in (p for p in files if p.endswith(TEXT_SUFFIXES) or "." not in Path(p).name):
        if not (ROOT / path).is_file() or any(pattern.search(path) for pattern in FORBIDDEN):
            continue  # refused by path already, or not a file
        text = (ROOT / path).read_text(errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_TEXT):
            failures.append(f"{path}: holds text shaped like a credential (not printed)")

    for path in (p for p in files if p.endswith(".py")):
        try:
            py_compile.compile(str(ROOT / path), doraise=True, cfile=str(ROOT / ".check_pycache"))
        except py_compile.PyCompileError as error:
            failures.append(f"{path}: does not compile: {error.msg}")
    (ROOT / ".check_pycache").unlink(missing_ok=True)

    for path in (p for p in files if p.endswith(".md")):
        for target in LINK.findall((ROOT / path).read_text()):
            if not target.startswith(("http://", "https://", "mailto:")) and not (ROOT / path).parent.joinpath(target).exists():
                failures.append(f"{path}: broken link to {target}")

    index = (ROOT / "docs" / "README.md").read_text()
    for path in (p for p in files if p.startswith("docs/") and p not in ("docs/README.md", "docs/roadmap.md")):
        if f"({path.removeprefix('docs/')})" not in index:
            failures.append(f"{path}: not listed in docs/README.md")

    if any(p.startswith("tests/") for p in files):
        if not VENV_PYTHON.exists():
            failures.append("tests: no .venv; run: uv venv .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt")
        elif subprocess.run([str(VENV_PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT).returncode:
            failures.append("tests: pytest failed")

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{'FAILED' if failures else 'OK'}: {len(files)} files checked, {len(failures)} problems")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
