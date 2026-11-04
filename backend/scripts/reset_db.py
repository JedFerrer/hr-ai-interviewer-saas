"""Reset only the disposable database created by run_owned_utility.py."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.owned_workspace import require_owned_workspace, owned_path


def main():
    root = require_owned_workspace()
    # Resolve and check every final target before the first deletion.
    targets = [owned_path(root / ("owned.db" + suffix)) for suffix in ("", "-journal", "-wal", "-shm")]
    for target in targets:
        if target.exists():
            target.unlink()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=os.environ.copy(), check=True, timeout=120)
    from scripts.seed_data import seed
    asyncio.run(seed())
    print("Owned database reset complete")

if __name__ == "__main__":
    main()
