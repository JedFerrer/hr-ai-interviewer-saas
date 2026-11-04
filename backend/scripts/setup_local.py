"""Create ordinary local environment files without printing secrets or replacing files."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[2]


def configure(root: Path) -> None:
    backend = root / "backend/.env"
    frontend = root / "frontend/.env.local"
    if any(p.exists() or p.is_symlink() for p in (backend, frontend)):
        raise ValueError("Environment file already exists; review both files manually. Nothing replaced.")
    db_name = "hr_local_" + secrets.token_hex(8) + ".db"
    if (root / "backend" / db_name).exists():
        raise ValueError("Selected database already exists; nothing changed.")
    proxy_secret = secrets.token_hex(64)
    backend_text = (root / "backend/.env.example").read_text(encoding="utf-8")
    backend_text = backend_text.replace("JWT_SECRET_KEY=\n", "JWT_SECRET_KEY=" + secrets.token_hex(64) + "\n")
    backend_text = backend_text.replace("PROXY_AUTH_SECRET=\n", "PROXY_AUTH_SECRET=" + proxy_secret + "\n")
    backend_text = backend_text.replace("./hr_interviewer.db", "./" + db_name)
    frontend_text = (root / "frontend/.env.example").read_text(encoding="utf-8")
    frontend_text = frontend_text.replace("PROXY_AUTH_SECRET=\n", "PROXY_AUTH_SECRET=" + proxy_secret + "\n")
    # Exclusive creation also refuses a file created after the initial check.
    # On partial failure retain the created file; never guess ownership for deletion.
    with backend.open("x", encoding="utf-8") as stream:
        stream.write(backend_text)
    with frontend.open("x", encoding="utf-8") as stream:
        stream.write(frontend_text)
    print("Created backend/.env and frontend/.env.local with private secrets. No database or provider call made.")


if __name__ == "__main__":
    try:
        configure(ROOT)
    except (ValueError, OSError):
        raise SystemExit("Setup refused or incomplete; inspect environment file existence locally. No existing file was replaced.") from None
