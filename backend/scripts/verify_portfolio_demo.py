"""Reproducible Windows demo acceptance through the real Next proxy.

Run after locked Python installation and frontend npm ci. Uses fresh run IDs,
real migrations, fixtures, HTTP routes and provider adapters. Prints no tokens.
Browser UI inspection remains a separate documented acceptance activity.
"""

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import run_portfolio_demo as runner


def cli(operation, run_id, *args, expected=0):
    result = subprocess.run(
        [sys.executable, str(Path(runner.__file__)), operation, run_id, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=540,
    )
    assert result.returncode == expected, (
        f"{operation}: unexpected exit {result.returncode}"
    )
    return json.loads(result.stdout) if expected == 0 else None


def wait_for(check, seconds=25):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = check()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError("Timed out waiting for expected persisted transition")


def request(client, method, path, status=200, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code == status, (
        f"{method} route: expected {status}, received {response.status_code}"
    )
    return response.json() if response.content else None


def messages(root, kind=None):
    result = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in (root / "mailbox").glob("*.json")
    ]
    return [m for m in result if kind is None or m["kind"] == kind]


def frontend_checks(root):
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    }
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    for script in ("lint", "typecheck", "test"):
        result = subprocess.run(
            ["npm.cmd", "run", script],
            cwd=root / "frontend",
            env=env,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, f"Frontend {script} failed"
    print(
        "PASS: isolated frontend lint, typecheck and tests; production build verified by startup"
    )


def walkthrough(run_id, state):
    root = runner.root_for(run_id)
    marker = runner.record(root, run_id)
    base = state["app"] + "/api/backend"
    common = {
        "base_url": base,
        "headers": {"X-Requested-With": "XMLHttpRequest"},
        "timeout": 30,
        "trust_env": False,
    }
    with (
        httpx.Client(**common) as admin,
        httpx.Client(**common) as other,
        httpx.Client(**common) as recruiter,
    ):
        for client, email in [
            (admin, "admin@example.com"),
            (other, "admin@example.org"),
            (recruiter, "recruiter@example.com"),
        ]:
            request(
                client,
                "POST",
                "/auth/login",
                json={"email": email, "password": "PortfolioDemo123!"},
            )
        jobs = request(admin, "GET", "/jobs")["jobs"]
        assert len(jobs) == 1
        job = jobs[0]
        created = request(
            admin,
            "POST",
            "/jobs",
            status=201,
            json={
                "title": "Fictional Recovery Engineer",
                "description": "Build Python FastAPI services with SQL and test reliable error recovery.",
                "required_skills": ["Python", "FastAPI", "SQL"],
                "interview_config": {"num_questions": 4},
            },
        )
        job = request(admin, "GET", "/jobs/" + created["job"]["id"])["job"]
        request(
            admin,
            "PUT",
            "/jobs/" + job["id"],
            json={"location": "Fictional remote office"},
        )
        request(other, "GET", "/jobs/" + job["id"], status=404)
        request(
            recruiter,
            "POST",
            "/team/invites",
            status=403,
            json={"email": "denied@example.com"},
        )
        request(recruiter, "GET", "/team/invites", status=403)

        def apply(name, email, filename):
            data = request(
                admin,
                "POST",
                "/interview/apply",
                data={
                    "job_token": job["interview_link_token"],
                    "candidate_name": name,
                    "candidate_email": email,
                },
                files={
                    "resume": (filename, (root / "fixtures" / filename).read_bytes())
                },
            )
            return data["candidate_id"]

        cli("fail-processing", run_id)
        strong = apply("Avery Example", "avery@example.com", "strong.pdf")
        detail_path = "/candidates/" + strong
        wait_for(lambda: request(admin, "GET", detail_path)["status"] == "error")
        cli("fail-email", run_id)
        request(admin, "POST", detail_path + "/retry-processing", status=202)
        wait_for(lambda: request(admin, "GET", detail_path)["status"] == "ready")
        assert not messages(root, "interview")
        request(admin, "POST", detail_path + "/retry-invite")
        invite = wait_for(lambda: messages(root, "interview"))[0]
        token = invite["link"].rsplit("/", 1)[1]
        assert request(admin, "GET", detail_path)["pre_screen"]["score"] == 92
        request(other, "GET", detail_path, status=404)
        request(admin, "POST", "/interview/session/" + token + "/start")
        answers = [
            "At Fictional Orchard Studio I owned a small backend feature, clarified requirements with the product team, and delivered a documented implementation. I also coordinated review and monitored the rollout so colleagues could understand the change.",
            "My testing approach covered malformed input, successful requests and unavailable dependencies. I created isolated datasets, compared actual responses with expected results, and reproduced a regression before fixing it. The new checks caught the same defect on subsequent runs.",
            "For a Python API I separate validation from business logic, make transaction boundaries explicit and handle timeouts. FastAPI schemas define the contract while SQL constraints preserve consistency. I keep retries bounded and provide actionable errors for operators.",
            "A slow database query needs measurement. I would collect an execution plan, compare index selectivity and inspect joins. After changing the query I would benchmark realistic data volumes and verify identical result rows before proposing the optimization.",
        ]
        for answer in answers:
            response = request(
                admin,
                "POST",
                "/interview/message",
                json={"interview_token": token, "message": answer},
            )
        assert response["is_complete"]
        detail = wait_for(
            lambda: (
                d
                if (d := request(admin, "GET", detail_path)).get("evaluation")
                else None
            )
        )
        assert detail["evaluation"]["overall_score"] == 8
        assert "SYNTHETIC" in detail["evaluation"]["summary"]
        assert len(detail["interview"]["transcript"]) >= 8
        before = len(messages(root))
        request(admin, "POST", detail_path + "/shortlist", json={})
        assert len(messages(root)) == before
        cli("fail-email", run_id)
        failed = request(
            admin,
            "POST",
            detail_path + "/send-notification",
            json={"kind": "shortlist"},
        )
        assert not failed["sent"]
        sent = request(
            admin,
            "POST",
            detail_path + "/send-notification",
            json={"kind": "shortlist"},
        )
        assert sent["sent"] and len(messages(root, "status")) == 1
        share = request(admin, "POST", detail_path + "/share", status=201)
        request(admin, "GET", "/public/report/" + share["token"])
        request(
            admin, "DELETE", detail_path + "/share/" + share["token_id"], status=204
        )
        request(admin, "GET", "/public/report/" + share["token"], status=404)
        review = apply("Riley Sample", "riley@example.com", "review.docx")
        wait_for(
            lambda: (
                request(admin, "GET", "/candidates/" + review)["status"]
                == "review_pending"
            )
        )
        before = len(messages(root))
        request(admin, "POST", "/candidates/" + review + "/reject-pre-screen", json={})
        assert len(messages(root)) == before
        request(
            admin,
            "POST",
            "/team/invites",
            status=201,
            json={"email": "joined@example.com"},
        )
        team_token = messages(root, "team")[0]["link"].rsplit("/", 1)[1]
        joined = request(
            recruiter,
            "POST",
            "/auth/invite/" + team_token + "/accept",
            status=201,
            json={
                "name": "Fictional Joined Recruiter",
                "password": "PortfolioDemo123!",
            },
        )
        assert joined["user"]["role"] == "recruiter"
        request(
            recruiter,
            "POST",
            "/team/invites",
            status=403,
            json={"email": "denied-again@example.com"},
        )
        request(admin, "GET", "/analytics/overview")
        with httpx.Client(trust_env=False) as browser:
            assert browser.get(state["mailbox"]).status_code == 401
            assert browser.get(state["mailbox"] + "/control/status").status_code == 403
            mail = browser.get(
                state["mailbox"], auth=("portfolio", marker["mailbox_token"])
            )
            assert mail.status_code == 200 and "Open invitation" in mail.text
            page = browser.get(state["app"] + "/login")
            assert "connect-src 'self'" in page.headers["content-security-policy"]
        log = (root / "runtime.log").read_text(encoding="utf-8", errors="replace")
        assert all(
            secret not in log
            for secret in (
                token,
                team_token,
                share["token"],
                marker["token"],
                marker["mailbox_token"],
            )
        )
        assert (root / "uploads/resumes").is_dir()
    print(
        "PASS: real proxy workflow, recovery, manual email, reports, roles, tenancy, mailbox protection, log redaction"
    )


def main():
    prefix = os.environ.get("HR_CHECK_RUN_ID", "verify-" + secrets.token_hex(6))
    run_ids = [prefix + "-a", prefix + "-b"]
    roots = [runner.root_for(run_id) for run_id in run_ids]
    # Check ordinary DB bytes without opening SQLite or reading any candidate data.
    baseline = {
        p: hashlib.sha256(p.read_bytes()).digest()
        for p in (
            runner.BACKEND / "hr_interviewer.db",
            runner.REPO / "hr_interviewer.db",
        )
        if p.is_file()
    }
    try:
        failure_id = "failure-" + secrets.token_hex(6)
        failure_root = runner.root_for(failure_id)
        failure_root.mkdir()
        failure_marker = {
            "purpose": "portfolio",
            "run_id": failure_id,
            "token": secrets.token_hex(32),
            "mailbox_token": secrets.token_hex(32),
        }
        (failure_root / ".hr-owned.json").write_text(json.dumps(failure_marker))
        (failure_root / "mailbox").mkdir()
        ports = [runner.choose_port(0) for _ in range(3)]
        (failure_root / "state.json").write_text(
            json.dumps(
                {"api_port": ports[0], "ui_port": ports[1], "control_port": ports[2]}
            )
        )
        env = runner.clean_env(failure_root, failure_marker, ports[0], ports[1])
        # Missing Alembic configuration is a deliberate startup failure before seeding.
        failed = subprocess.run(
            [sys.executable, str(Path(runner.__file__)), "_supervise", failure_id],
            cwd=failure_root.parent,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
        assert failed.returncode == 0 and not failure_root.exists()
        print("PASS: partial startup failure removes only its owned run")
        lease_id = prefix + "-lease"
        old_lease = os.environ.get("HR_DEMO_LEASE_SECONDS")
        try:
            os.environ["HR_DEMO_LEASE_SECONDS"] = "1"
            cli("start", lease_id, expected=1)
            assert not runner.root_for(lease_id).exists()
        finally:
            if old_lease is None:
                os.environ.pop("HR_DEMO_LEASE_SECONDS", None)
            else:
                os.environ["HR_DEMO_LEASE_SECONDS"] = old_lease
        print("PASS: expired CI lease cancels preparation and removes owned resources")
        state = cli("start", run_ids[0])
        frontend_checks(roots[0])
        walkthrough(run_ids[0], state)
        cli("start", run_ids[1])
        first_marker, second_marker = [
            runner.record(p, r) for p, r in zip(roots, run_ids, strict=True)
        ]
        assert first_marker["token"] != second_marker["token"]
        assert first_marker["mailbox_token"] != second_marker["mailbox_token"]
        assert len(messages(roots[0])) > 0 and not messages(roots[1])
        assert roots[0] != roots[1] and all((p / "owned.db").exists() for p in roots)
        with socket.socket() as conflict:
            conflict.bind(("127.0.0.1", 0))
            conflict.listen()
            conflict_id = "conflict-" + secrets.token_hex(6)
            cli(
                "start",
                conflict_id,
                "--api-port",
                str(conflict.getsockname()[1]),
                expected=1,
            )
            assert not runner.root_for(conflict_id).exists()
        assert cli("status", run_ids[0])["status"] == "ready"
        assert cli("status", run_ids[1])["status"] == "ready"
        print(
            "PASS: concurrent runs isolate database, mailbox and ownership secrets; occupied port leaves no run"
        )
    finally:
        for run_id, root in zip(run_ids, roots, strict=True):
            if root.exists():
                cli("stop", run_id)
                assert not root.exists()
            assert cli("stop", run_id)["status"] == "stopped"
        assert all(
            hashlib.sha256(p.read_bytes()).digest() == digest
            for p, digest in baseline.items()
        )
        print(
            "PASS: owned shutdown, repeated stop, cleanup and ordinary database byte preservation"
        )


if __name__ == "__main__":
    main()
