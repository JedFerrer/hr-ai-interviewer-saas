"""Canonical release checks. Run from the repository root with locked Python."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def environment():
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT",
        "USERPROFILE", "LOCALAPPDATA", "PLAYWRIGHT_BROWSERS_PATH", "HR_CHECK_RUN_ID", "HR_DEMO_LEASE_SECONDS", "HR_CHECK_HISTORY_ROOT",
    }}
    env.update(PYTHONUTF8="1", NEXT_TELEMETRY_DISABLED="1")
    return env


def run(args, cwd=ROOT, timeout=900):
    subprocess.run(args, cwd=cwd, env=environment(), check=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["lint", "backend", "frontend", "demo", "browser", "dependencies", "secrets"])
    args = parser.parse_args()
    if args.check == "lint":
        run([sys.executable, "-m", "ruff", "check", "backend", "src", "scripts", "run_evaluation.py", "run_interview.py"])
    elif args.check == "backend":
        run([sys.executable, "backend/scripts/verify_release_baseline.py", "--tests"])
        run([sys.executable, "backend/scripts/verify_release_baseline.py"])
    elif args.check == "frontend":
        # No inherited .env, old build or node_modules. Install exclusively from lock.
        with tempfile.TemporaryDirectory(prefix="hr-frontend-check-") as directory:
            dest = Path(directory) / "frontend"
            shutil.copytree(ROOT / "frontend", dest, ignore=shutil.ignore_patterns(
                "node_modules", ".next", ".env*", "*.tsbuildinfo"))
            npm = "npm.cmd" if os.name == "nt" else "npm"
            run([npm, "ci", "--fetch-retries=0"], dest)
            for command in ("lint", "typecheck", "test", "build"):
                run([npm, "run", command], dest)
    elif args.check in {"demo", "browser"}:
        os.environ["HR_DEMO_LEASE_SECONDS"] = "1500"
        script = "verify_portfolio_demo.py" if args.check == "demo" else "verify_browser_smoke.py"
        run([sys.executable, str(ROOT / "backend/scripts" / script)], timeout=1800)
    else:
        run([sys.executable, str(ROOT / "scripts" / ("check_" + args.check + ".py"))])


if __name__ == "__main__":
    main()
