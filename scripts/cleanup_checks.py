"""CI fallback: authenticate stop for only this job's known owned demo IDs."""
import os
import subprocess
import sys
from pathlib import Path


def main():
    prefix = os.environ["HR_CHECK_RUN_ID"]
    runner = Path(__file__).resolve().parents[1] / "backend/scripts/run_portfolio_demo.py"
    failed = False
    for suffix in ("", "-a", "-b", "-lease"):
        result = subprocess.run([sys.executable, str(runner), "stop", prefix + suffix],
                                capture_output=True, timeout=240)
        failed |= result.returncode != 0
    print("Owned CI cleanup: " + ("refused; inspect ownership" if failed else "complete"))
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
