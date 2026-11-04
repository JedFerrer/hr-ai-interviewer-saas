"""Local workflow invariants and toolchain validation; not hosted-run proof."""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "actions/checkout": "34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-node": "49933ea5288caeca8642d1e84afbd3f7d6820020",
}


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_source.py")], check=True)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "scripts"),
                    "-p", "test_source_metadata.py"], check=True)
    assert sys.version_info[:3] == (3, 11, 9), "Use Python 3.11.9"
    assert subprocess.check_output(["node", "--version"], text=True).strip() == "v22.16.0"
    assert subprocess.check_output(["npm.cmd", "--version"], text=True).strip() == "10.9.2"
    workflow = yaml.load((ROOT / ".github/workflows/quality.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    assert set(workflow["jobs"]) == {"backend", "frontend", "windows-demo", "browser-smoke", "dependencies", "secrets"}
    for name, job in workflow["jobs"].items():
        assert job["runs-on"] == "windows-2022" and int(job["timeout-minutes"]) <= 35
        for step in job["steps"]:
            if "uses" in step:
                action, revision = step["uses"].split("@")
                assert re.fullmatch("[a-f0-9]{40}", revision) and PINS[action] == revision
                if action == "actions/checkout":
                    assert step["with"]["persist-credentials"] == "false"
                    if name == "secrets":
                        assert step["with"]["fetch-depth"] == "0"
    config = json.loads((ROOT / "renovate.json").read_text())
    assert "pip-compile" in config["enabledManagers"]
    for path in ("backend/requirements.lock", "security/requirements.lock"):
        assert any(re.search(pattern.strip("/"), path) for pattern in config["pip-compile"]["managerFilePatterns"])
        header = (ROOT / path).read_text().splitlines()[1]
        assert "uv pip compile" in header and "--generate-hashes" in header
        assert ".release-work" not in header
    print("PASS: pinned toolchain and workflow safety invariants (hosted execution pending)")


if __name__ == "__main__":
    main()
