"""Audit exact locks. Every finding fails until remediated (no accepted exceptions)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / ".security-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    failures = False
    for lock in ("backend/requirements.lock", "security/requirements.lock"):
        with tempfile.TemporaryDirectory(prefix="hr-audit-") as directory:
            report = Path(directory) / "audit.json"
            result = subprocess.run([
                str(SCANNER), "-m", "pip_audit",
                "-r", str(ROOT / lock), "--require-hashes", "--disable-pip",
                "--format", "json", "--output", str(report),
            ], capture_output=True, timeout=300)
            if result.returncode not in (0, 1) or not report.exists():
                raise RuntimeError("Python advisory scanner unavailable")
            data = json.loads(report.read_text())
            findings = [(d["name"], d["version"], v["id"], v["fix_versions"])
                        for d in data["dependencies"] for v in d["vulns"]]
            for finding in findings:
                print(lock, *finding)
            failures |= bool(findings) or result.returncode != 0
            print(f"{lock}: {len(data['dependencies'])} packages, {len(findings)} advisories")
    result = subprocess.run(["npm.cmd" if os.name == "nt" else "npm", "audit", "--json"],
                            cwd=ROOT / "frontend", capture_output=True, timeout=180)
    data = json.loads(result.stdout)
    if "vulnerabilities" not in data:
        raise RuntimeError("npm advisory scanner unavailable")
    for name, finding in data["vulnerabilities"].items():
        print("npm:", name, finding["severity"], ",".join(finding["nodes"]))
    print("npm totals:", data["metadata"]["vulnerabilities"])
    failures |= result.returncode != 0
    return int(failures)


if __name__ == "__main__":
    sys.exit(main())
