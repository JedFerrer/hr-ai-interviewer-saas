"""Owned portfolio lifecycle. No saved PID is ever used to terminate a process."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
OPENER = build_opener(ProxyHandler({}))
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def root_for(run_id):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}", run_id):
        raise ValueError("Run ID must be 1-48 letters, digits, hyphens or underscores")
    return Path(tempfile.gettempdir()).resolve() / ("hr-owned-portfolio-" + run_id)


def record(root, run_id):
    if root != root_for(run_id) or root.resolve() != root or root.is_symlink():
        raise ValueError("Refusing non-owned or redirected run path")
    marker_path = root / ".hr-owned.json"
    if marker_path.resolve() != marker_path:
        raise ValueError("Refusing redirected ownership record")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if (
        marker.get("purpose") != "portfolio"
        or marker.get("run_id") != run_id
        or len(marker.get("token", "")) != 64
    ):
        raise ValueError("Invalid ownership record; refusing action")
    return marker


def clean(root, run_id, token):
    marker = record(root, run_id)
    if not hmac.compare_digest(marker["token"], token):
        raise ValueError("Ownership changed; refusing cleanup")
    # Do not follow links/junctions, including links planted inside a run.
    # Next's route cache can exceed MAX_PATH after real browser navigation.
    # Use the extended Windows path only AFTER validating the canonical root.
    native_root = "\\\\?\\" + str(root) if os.name == "nt" else str(root)
    for directory, dirs, files in os.walk(native_root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            if (
                path.is_symlink()
                or getattr(info, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT
            ):
                raise ValueError("Redirected run content; refusing cleanup")
    # Keep the ownership proof until all generated content has been removed.
    for entry in os.scandir(native_root):
        if entry.name == ".hr-owned.json":
            continue
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.path)
        else:
            os.unlink(entry.path)
    os.unlink(os.path.join(native_root, ".hr-owned.json"))
    os.rmdir(native_root)


def clean_env(root, marker, api_port, ui_port):
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    }
    env.update(
        ENVIRONMENT="development",
        PORTFOLIO_DEMO="1",
        HR_DEMO_RUN_ID=marker["run_id"],
        HR_OWNED_WORKSPACE=str(root),
        HR_OWNED_TOKEN=marker["token"],
        DATABASE_URL="sqlite+aiosqlite:///" + (root / "owned.db").as_posix(),
        JWT_SECRET_KEY=secrets.token_hex(64),
        PROXY_AUTH_SECRET=secrets.token_hex(32),
        TRUSTED_PROXY_IPS='["127.0.0.1"]',
        PYTHONPATH=str(root / "backend"),
        PYTHONUTF8="1",
        APP_URL=f"http://127.0.0.1:{ui_port}",
        API_URL=f"http://127.0.0.1:{api_port}",
        ALLOWED_ORIGINS=json.dumps([f"http://127.0.0.1:{ui_port}"]),
        BACKEND_INTERNAL_URL=f"http://127.0.0.1:{api_port}",
        HR_API_PORT=str(api_port),
        PORT=str(ui_port),
        NEXT_TELEMETRY_DISABLED="1",
        NODE_ENV="production",
    )
    # Parser temporary files also stay within this run.
    (root / "tmp").mkdir()
    env.update(HR_DEMO_TEMP=str(root / "tmp"))
    return env


def choose_port(requested):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", requested))
        return sock.getsockname()[1]


def fetch(url, *, token=None, method="GET", nonce=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if nonce:
        headers["X-Portfolio-Nonce"] = nonce
    with OPENER.open(
        Request(url, headers=headers, method=method), timeout=2
    ) as response:
        return response.read()


def control(root, marker, action):
    state_path = root / "state.json"
    if state_path.resolve() != state_path:
        raise ValueError("Redirected state refused")
    state = json.loads(state_path.read_text())
    port = int(state["control_port"])
    nonce = secrets.token_hex(32)
    reply = json.loads(
        fetch(
            f"http://127.0.0.1:{port}/control/proof", token=marker["token"], nonce=nonce
        )
    )
    expected = hmac.new(
        marker["token"].encode(), nonce.encode(), hashlib.sha256
    ).hexdigest()
    if reply.get("run_id") != marker["run_id"] or not hmac.compare_digest(
        reply.get("proof", ""), expected
    ):
        raise ValueError("Supervisor identity mismatch; refusing action")
    return json.loads(
        fetch(
            f"http://127.0.0.1:{port}/control/{action}",
            token=marker["token"],
            method="GET" if action == "status" else "POST",
        )
    )


class Children:
    """Live Popen handles, plus a Windows job that kills only assigned children."""

    def __init__(self):
        self.processes = []
        self.job = None
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
            self.kernel.AssignProcessToJobObject.argtypes = [
                wintypes.HANDLE,
                wintypes.HANDLE,
            ]
            self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.job = self.kernel.CreateJobObjectW(None, None)
            if not self.job:
                raise OSError("Cannot create owned Windows process job")

            class Basic(ctypes.Structure):
                _fields_ = [
                    ("process_time", ctypes.c_longlong),
                    ("job_time", ctypes.c_longlong),
                    ("flags", wintypes.DWORD),
                    ("min_ws", ctypes.c_size_t),
                    ("max_ws", ctypes.c_size_t),
                    ("processes", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t),
                    ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD),
                ]

            class Extended(ctypes.Structure):
                _fields_ = [
                    ("basic", Basic),
                    ("io", ctypes.c_ulonglong * 6),
                    ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t),
                    ("peak_process", ctypes.c_size_t),
                    ("peak_job", ctypes.c_size_t),
                ]

            limits = Extended()
            limits.basic.flags = (
                0x2000  # KILL_ON_JOB_CLOSE: supervisor death stops its children.
            )
            self.kernel.SetInformationJobObject.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            if not self.kernel.SetInformationJobObject(
                self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                self.kernel.CloseHandle(self.job)
                raise OSError("Cannot establish owned process lifetime")

    def spawn(self, args, *, cwd, env, output):
        child = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=output,
            stderr=output,
            stdin=subprocess.DEVNULL,
            creationflags=HIDDEN,
        )
        self.processes.append(child)
        if self.job and not self.kernel.AssignProcessToJobObject(
            self.job, int(child._handle)
        ):
            child.terminate()
            child.wait(timeout=10)
            raise OSError("Cannot assign child to owned Windows job")
        return child

    def stop(self):
        if self.job:
            self.kernel.TerminateJobObject(self.job, 0)
        for child in self.processes:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=15)
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None


def mailbox_html(root, app_url):
    parts = [
        "<!doctype html><meta name='viewport' content='width=device-width'><title>Portfolio mailbox</title>",
        "<h1>Captured fictional email</h1><p>Local demo only. Nothing was delivered externally.</p>",
        "<p><a href='/'>Refresh mailbox</a></p>",
    ]
    for file in sorted(
        (root / "mailbox").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        message = json.loads(file.read_text(encoding="utf-8"))
        parts.append(
            "<article><h2>"
            + html.escape(message["subject"])
            + "</h2><p>To: "
            + html.escape(message["recipient"])
            + "</p><pre style='white-space:pre-wrap'>"
            + html.escape(message["body"])
            + "</pre>"
        )
        link = message.get("link")
        if link:
            parsed = urlsplit(link)
            expected = urlsplit(app_url)
            if (
                (parsed.scheme, parsed.netloc) == (expected.scheme, expected.netloc)
                and not parsed.query
                and not parsed.fragment
                and re.fullmatch(
                    r"/(?:interview/session|accept-invite)/[A-Za-z0-9_-]+", parsed.path
                )
            ):
                parts.append(
                    "<a rel='noreferrer' href='"
                    + html.escape(link, quote=True)
                    + "'>Open invitation</a>"
                )
        parts.append("</article><hr>")
    return "".join(parts).encode()


def supervise(root, run_id):
    marker = record(root, run_id)
    os.chdir(root)
    from owned_workspace import require_owned_workspace

    require_owned_workspace()
    state = json.loads((root / "state.json").read_text())
    stop = threading.Event()
    # A surviving CI supervisor expires after cancellation, then uses owned cleanup.
    lease = os.environ.get("HR_DEMO_LEASE_SECONDS")
    if lease:
        timer = threading.Timer(int(lease), stop.set)
        timer.daemon = True
        timer.start()
    state["status"] = "starting"
    children = Children()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # No request paths, credentials, bodies or raw errors in logs.

        def respond(self, status, payload, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            )
            if status == 401:
                self.send_header("WWW-Authenticate", 'Basic realm="Portfolio mailbox"')
            self.end_headers()
            self.wfile.write(
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            try:
                current = record(root, run_id)
                if not hmac.compare_digest(current["token"], marker["token"]):
                    raise ValueError("ownership changed")
            except (ValueError, OSError):
                return self.respond(409, {"error": "Ownership changed; action refused"})
            if self.path.startswith("/control/"):
                if not hmac.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + marker["token"]
                ):
                    return self.respond(403, {})
                action = self.path.removeprefix("/control/")
                if action == "proof":
                    nonce = self.headers.get("X-Portfolio-Nonce", "")
                    return self.respond(
                        200,
                        {
                            "run_id": run_id,
                            "proof": hmac.new(
                                marker["token"].encode(), nonce.encode(), hashlib.sha256
                            ).hexdigest(),
                        },
                    )
                if action == "status":
                    return self.respond(
                        200,
                        {
                            k: state[k]
                            for k in (
                                "status",
                                "ui_port",
                                "api_port",
                                "control_port",
                                "error",
                            )
                            if k in state
                        },
                    )
                if self.command != "POST":
                    return self.respond(405, {})
                if action == "stop":
                    self.respond(200, {"status": "stopping"})
                    stop.set()
                    return
                if (
                    action in {"fail-processing", "fail-email"}
                    and state["status"] == "ready"
                ):
                    (root / action).write_text("one-shot", encoding="utf-8")
                    return self.respond(200, {"status": "armed"})
                return self.respond(404, {})
            expected = (
                "Basic "
                + base64.b64encode(
                    ("portfolio:" + marker["mailbox_token"]).encode()
                ).decode()
            )
            if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
                return self.respond(401, {})
            if self.path != "/" or self.command != "GET":
                return self.respond(404, {})
            self.respond(
                200,
                mailbox_html(root, os.environ["APP_URL"]),
                "text/html; charset=utf-8",
            )

    server = ThreadingHTTPServer(("127.0.0.1", state["control_port"]), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log = (root / "runtime.log").open("wb")
    phase = "preparation"
    try:
        for command in (
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            [sys.executable, "-m", "app.demo.seed"],
            [
                shutil.which("node"),
                str(root / "frontend/node_modules/next/dist/bin/next"),
                "build",
            ],
        ):
            phase = (
                "frontend build"
                if command[-1] == "build"
                else "migration"
                if "alembic" in command
                else "fixture seed"
            )
            cwd = root / "frontend" if command[-1] == "build" else root
            child = children.spawn(command, cwd=cwd, env=os.environ.copy(), output=log)
            preparation_deadline = time.monotonic() + 180
            while child.poll() is None:
                if stop.wait(0.25):
                    raise RuntimeError("Startup cancelled by owned stop")
                if time.monotonic() >= preparation_deadline:
                    raise TimeoutError("Preparation step exceeded 180 seconds")
            if child.returncode != 0:
                raise RuntimeError(
                    "Migration, fixture preparation or frontend build failed"
                )
        phase = "service readiness"
        api = children.spawn(
            [sys.executable, "-m", "app.demo.serve"],
            cwd=root,
            env=os.environ.copy(),
            output=log,
        )
        ui = children.spawn(
            [
                shutil.which("node"),
                "--import",
                "./server/demo-network.mjs",
                "server.mjs",
            ],
            cwd=root / "frontend",
            env=os.environ.copy(),
            output=log,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if stop.is_set() or api.poll() is not None or ui.poll() is not None:
                raise RuntimeError("Service exited before readiness")
            try:
                assert (
                    json.loads(fetch(os.environ["API_URL"] + "/health"))["status"]
                    == "ok"
                )
                assert (
                    json.loads(fetch(os.environ["APP_URL"] + "/api/backend/health"))[
                        "status"
                    ]
                    == "ok"
                )
                assert b"<html" in fetch(os.environ["APP_URL"] + "/login")
                nonce = secrets.token_hex(32)
                proof = (
                    hmac.new(marker["token"].encode(), nonce.encode(), hashlib.sha256)
                    .hexdigest()
                    .encode()
                )
                assert (
                    fetch(os.environ["APP_URL"] + "/__portfolio-proof", nonce=nonce)
                    == proof
                )
                assert (
                    fetch(
                        os.environ["APP_URL"] + "/api/backend/__portfolio-proof",
                        nonce=nonce,
                    )
                    == proof
                )
                break
            except (OSError, AssertionError, ValueError):
                stop.wait(0.5)
        else:
            raise RuntimeError("Readiness timed out; check ports and installation")
        state["status"] = "ready"
        while not stop.wait(0.5):
            if api.poll() is not None or ui.poll() is not None:
                raise RuntimeError("Owned service stopped unexpectedly")
    except Exception as exc:  # noqa: BLE001 - supervisor must stop owned children on every startup failure
        state["error"] = phase + ": " + type(exc).__name__
        state["status"] = "failed"
        # Sanitized, bounded message; detailed provider/content exceptions omitted.
        (root / "failure.txt").write_text(
            "Demo startup/runtime failed. Check Node 22, locked Python dependencies, installed frontend dependencies and available ports."
        )
        stop.wait(3)
    finally:
        children.stop()
        server.shutdown()
        server.server_close()
        log.close()
        os.chdir(tempfile.gettempdir())
        clean(root, run_id, marker["token"])


def start(args):
    if os.name != "nt":
        raise ValueError("This launcher is currently verified only for Windows")
    if os.environ.get(
        "ENVIRONMENT", "development"
    ).lower().strip() != "development" or any(
        os.environ.get(key)
        for key in (
            "DATABASE_URL",
            "LLM_PROVIDER",
            "LLM_MODEL",
            "LLM_FALLBACK_PROVIDERS",
            "SUPABASE_URL",
            "REDIS_URL",
            "HR_ALLOW_PROVIDERS",
            "NODE_OPTIONS",
            "PYTHONPATH",
        )
    ):
        raise ValueError(
            "Clear inherited database/provider/runtime overrides before starting"
        )
    if not (REPO / "frontend/node_modules/next/dist/bin/next").is_file():
        raise ValueError("Run npm ci in frontend before starting")
    root = root_for(args.run_id)
    if root.exists():
        raise ValueError("Run already exists; use status/stop or choose a fresh run ID")
    ports = [choose_port(p) for p in (args.api_port, args.ui_port, args.mailbox_port)]
    if len(set(ports)) != 3:
        raise ValueError("API, frontend and mailbox ports must differ")
    root.mkdir()
    marker = {
        "purpose": "portfolio",
        "run_id": args.run_id,
        "token": secrets.token_hex(32),
        "mailbox_token": secrets.token_urlsafe(32),
    }
    (root / ".hr-owned.json").write_text(json.dumps(marker), encoding="utf-8")
    child = None
    try:
        for name in ("app", "scripts", "alembic"):
            shutil.copytree(
                BACKEND / name,
                root / "backend" / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env*"),
            )
        shutil.copytree(
            BACKEND / "tests/fixtures/portfolio",
            root / "backend/tests/fixtures/portfolio",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(
            REPO / "frontend",
            root / "frontend",
            ignore=shutil.ignore_patterns(
                ".env*", ".next", "*.tsbuildinfo", ".git", "node_modules"
            ),
        )
        # A physical dependency copy prevents module resolution escaping the run.
        copied = subprocess.run(
            [
                "robocopy",
                str(REPO / "frontend/node_modules"),
                str(root / "frontend/node_modules"),
                "/E",
                "/NFL",
                "/NDL",
                "/NJH",
                "/NJS",
                "/NP",
                "/R:0",
                "/W:0",
                "/MT:8",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
            creationflags=HIDDEN,
            check=False,
        )
        if copied.returncode >= 8:
            raise RuntimeError(
                "Dependency copy failed; run npm ci and check disk space"
            )
        config = (
            (BACKEND / "alembic.ini")
            .read_text()
            .replace("%(here)s/alembic", (root / "backend/alembic").as_posix())
        )
        (root / "alembic.ini").write_text(config)
        (root / "mailbox").mkdir()
        state = {
            "status": "starting",
            "api_port": ports[0],
            "ui_port": ports[1],
            "control_port": ports[2],
        }
        (root / "state.json").write_text(json.dumps(state))
        env = clean_env(root, marker, ports[0], ports[1])
        if os.environ.get("HR_DEMO_LEASE_SECONDS"):
            seconds = int(os.environ["HR_DEMO_LEASE_SECONDS"])
            if not 1 <= seconds <= 1800:
                raise ValueError("Demo lease must be 1-1800 seconds")
            env["HR_DEMO_LEASE_SECONDS"] = str(seconds)
        child = subprocess.Popen(
            [
                sys.executable,
                str(root / "backend/scripts/run_portfolio_demo.py"),
                "_supervise",
                args.run_id,
            ],
            cwd=Path(tempfile.gettempdir()).resolve(),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=HIDDEN,
        )
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(
                    "Demo startup failed; verify prerequisites and port availability. Owned resources were cleaned if ownership remained valid."
                )
            try:
                status = control(root, marker, "status")
                if status["status"] == "ready":
                    print(
                        json.dumps(
                            {
                                "run_id": args.run_id,
                                "status": "ready",
                                "app": f"http://127.0.0.1:{ports[1]}",
                                "mailbox": f"http://127.0.0.1:{ports[2]}",
                                "fixtures": str(root / "fixtures"),
                                "credentials_file": str(root / "credentials.txt"),
                            }
                        )
                    )
                    (root / "credentials.txt").write_text(
                        "Fictional app accounts: admin@example.com, recruiter@example.com, admin@example.org, recruiter@example.org\nApp password: PortfolioDemo123!\nMailbox user: portfolio\nMailbox password: "
                        + marker["mailbox_token"],
                        encoding="utf-8",
                    )
                    return
                if status["status"] == "failed":
                    raise RuntimeError(
                        "Demo startup failed at "
                        + status.get("error", "preparation")
                        + ". Check Node 22, Python dependencies, frontend npm ci and available ports."
                    )
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        raise RuntimeError("Demo startup exceeded 300 seconds")
    except BaseException:
        if child is None:
            clean(root, args.run_id, marker["token"])
        elif child.poll() is not None and root.exists():
            # Covers failures before the supervisor could enter its cleanup block
            # (for example another process acquiring the control port).
            clean(root, args.run_id, marker["token"])
        elif child.poll() is None:
            try:
                control(root, marker, "stop")
                child.wait(timeout=200)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass  # Never kill a PID or delete resources with uncertain ownership.
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=[
            "start",
            "status",
            "stop",
            "fail-processing",
            "fail-email",
            "_supervise",
        ],
    )
    parser.add_argument("run_id")
    parser.add_argument("--api-port", type=int, default=0)
    parser.add_argument("--ui-port", type=int, default=0)
    parser.add_argument("--mailbox-port", type=int, default=0)
    args = parser.parse_args()
    try:
        root = root_for(args.run_id)
        if args.operation == "start":
            start(args)
        elif args.operation == "_supervise":
            supervise(root, args.run_id)
        elif not root.exists():
            print(json.dumps({"status": "stopped", "run_id": args.run_id}))
        else:
            marker = record(root, args.run_id)
            result = control(root, marker, args.operation)
            if args.operation == "stop":
                deadline = time.monotonic() + 120
                while root.exists() and time.monotonic() < deadline:
                    time.sleep(0.25)
                if root.exists():
                    raise ValueError(
                        "Shutdown requested; cleanup incomplete. Do not delete an unverified run."
                    )
                result = {"status": "stopped", "cleanup": "complete"}
            print(json.dumps(result))
    except (ValueError, OSError, RuntimeError) as exc:
        # These are local sanitized lifecycle errors, never HTTP/provider content.
        if isinstance(exc, OSError):
            print(
                "REFUSING: unavailable port, supervisor or owned file; no PID termination or unverified cleanup attempted.",
                file=sys.stderr,
            )
        else:
            print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
