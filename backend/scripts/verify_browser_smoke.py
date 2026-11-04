"""Own a disposable demo for a real Chromium UI journey; never print browser errors."""
import json
import os
import secrets
import subprocess
from pathlib import Path

import run_portfolio_demo as runner
from verify_portfolio_demo import cli


def main():
    run_id = os.environ.get("HR_CHECK_RUN_ID", "browser-" + secrets.token_hex(6))
    root = runner.root_for(run_id)
    try:
        state = cli("start", run_id)
        marker = runner.record(root, run_id)
        env = {k: v for k, v in os.environ.items() if k.upper() in {
            "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT",
            "USERPROFILE", "LOCALAPPDATA", "PLAYWRIGHT_BROWSERS_PATH",
        }}
        result = subprocess.run(
            ["node", str(Path(__file__).resolve().parents[2] / "frontend/tests/browser-smoke.mjs")],
            input=json.dumps({**state, "mailboxPassword": marker["mailbox_token"],
                              "resume": str(root / "fixtures/strong.pdf")}),
            text=True, capture_output=True, env=env, timeout=240,
        )
        # Playwright errors can include token URLs and form values. Never relay them.
        if result.returncode:
            for phase in ("launch", "login", "application", "invitation", "interview", "evaluation", "evaluation-list", "evaluation-tab", "evaluation-score", "evaluation-summary"):
                if result.stderr.strip() == "Browser phase failed: " + phase:
                    print("Browser phase failed: " + phase)
            raise RuntimeError("Browser smoke failed; sensitive diagnostics withheld")
        print("PASS: Chromium login, application, authenticated invitation, interview, evaluation")
    finally:
        if root.exists():
            cli("stop", run_id)
        assert not root.exists(), "Owned browser demo cleanup incomplete"
        print("PASS: browser demo resources removed")


if __name__ == "__main__":
    main()
