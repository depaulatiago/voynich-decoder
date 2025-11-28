import subprocess
import sys
from pathlib import Path


def test_smoke_runs():
    root = Path(__file__).resolve().parents[1]
    sh = root / 'scripts' / 'smoke_run.sh'
    assert sh.exists(), 'smoke_run.sh missing'
    # run smoke script
    p = subprocess.run(["/bin/bash", str(sh)], cwd=str(root.parent))
    assert p.returncode == 0, f"smoke script failed (code {p.returncode})"
