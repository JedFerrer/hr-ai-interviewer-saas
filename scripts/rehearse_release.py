"""Rehearse the proposed manifest in a clean owned copy, including fresh installs.

Only Git history is read from the original checkout; no application state is copied.
Run with Python 3.11.9, Node 22.16.0, npm 10.9.2, uv 0.12.1 installed.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from check import environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", nargs="+", choices=["lint", "backend", "frontend", "demo", "browser", "dependencies", "secrets"],
                        default=["lint", "backend", "frontend", "demo", "browser", "dependencies", "secrets"])
    args = parser.parse_args()
    results = {}
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_source.py")], check=True)
    with tempfile.TemporaryDirectory(prefix="hr-release-rehearsal-") as directory:
        copy = Path(directory).resolve()
        for name in (ROOT / "release/RELEASE_SOURCE_FILES.txt").read_text().splitlines():
            source, destination = ROOT / name, copy / name
            if not source.resolve().is_relative_to(ROOT) or not destination.resolve().is_relative_to(copy):
                raise ValueError("Manifest path escapes owned source")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        env = environment()
        env["HR_CHECK_HISTORY_ROOT"] = str(ROOT)
        python = str(copy / ".venv/Scripts/python.exe")
        for command in [
            ["uv", "venv", ".venv", "--python", "3.11.9"],
            ["uv", "pip", "sync", "backend/requirements.lock", "--python", python, "--require-hashes"],
            ["uv", "venv", ".security-venv", "--python", "3.11.9"],
            ["uv", "pip", "sync", "security/requirements.lock", "--python", ".security-venv/Scripts/python.exe", "--require-hashes"],
            ["npm.cmd", "--prefix", "frontend", "ci", "--fetch-retries=0"],
            ["node", "frontend/node_modules/playwright/cli.js", "install", "chromium"],
            [python, "scripts/validate_ci.py"],
            [python, "scripts/validate_source.py"],
        ]:
            subprocess.run(command, cwd=copy, env=env, timeout=600, check=True)
        for check in args.checks:
            print("REHEARSAL START: " + check, flush=True)
            result = subprocess.run([python, "scripts/check.py", check], cwd=copy, env=env, timeout=2100)
            results[check] = result.returncode
            print(f"REHEARSAL RESULT: {check} exit {result.returncode}", flush=True)
    print("REHEARSAL CLEANUP: complete", flush=True)
    print(json.dumps(results, sort_keys=True))
    return int(any(results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
