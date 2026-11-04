"""Scan proposed source and available publication refs; never output secret values."""
import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from validate_source import DIGEST, MANIFEST, digest_for, selected_paths

ROOT = Path(__file__).resolve().parents[1]
HISTORY_ROOT = Path(os.environ.get("HR_CHECK_HISTORY_ROOT", ROOT)).resolve()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=HISTORY_ROOT)


def text_content(data, path):
    if path.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "\n".join(archive.read(n).decode("utf-8") for n in archive.namelist() if n.endswith(".xml"))
    if path.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return json.dumps(pdf.metadata) + "\n" + "\n".join(p.extract_text() or "" for p in pdf.pages)
    if path.endswith(".png"):
        # Pixel content needs human review. Scan textual metadata too.
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            return json.dumps(image.info)
    return data.decode("utf-8")


def verified_digest_text(data, expected=None):
    """Remove only recomputed source hashes, retaining paths for normal scanning.

    Historical sidecars must supply metadata recomputed from their own Git tree.
    Extra fields, changed hashes or stale metadata fail closed before filtering.
    """
    document = json.loads(data)
    if document != (digest_for(selected_paths()) if expected is None else expected):
        raise ValueError("Source digest is not the exact recomputed metadata")
    document["digest"] = "verified-sha256"
    for row in document["files"]:
        row["sha256"] = "verified-sha256"
    return json.dumps(document).encode()


def historical_digest(commit, read):
    """Recompute metadata from immutable Git blobs, never executing historical code."""
    names = read(commit, MANIFEST).decode("utf-8").splitlines()
    if names != sorted(set(names)) or DIGEST not in names:
        raise ValueError("Invalid historical source manifest")
    rows = []
    for name in names:
        if not name or "\\" in name or name.startswith("/") or ":" in name or ".." in name.split("/"):
            raise ValueError("Invalid historical source path")
        if name == DIGEST:
            continue
        data = read(commit, name)
        if Path(name).suffix not in {".pdf", ".docx", ".png"}:
            data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
        rows.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    aggregate = "".join(f"{row['sha256']}  {row['path']}\n" for row in rows)
    return {"format": "sha256-lf-text-path-lines-v2", "count": len(rows),
            "digest": hashlib.sha256(aggregate.encode()).hexdigest(), "files": rows}


def verified_history_metadata(refs):
    """Only filter digest blobs that exactly match a reachable containing commit."""
    verified = {}
    blobs = {}
    def read(commit, path):
        oid = git("rev-parse", commit + ":" + path).decode().strip()
        if oid not in blobs:
            blobs[oid] = git("cat-file", "blob", oid)
        return blobs[oid]
    for commit in git("rev-list", *refs).decode().splitlines():
        entries = git("ls-tree", commit, "--", DIGEST).decode().splitlines()
        if not entries:
            continue
        oid = entries[0].split()[2]
        if oid not in verified:
            verified[oid] = verified_digest_text(read(commit, DIGEST), historical_digest(commit, read))
    return verified


def same_reviewed_baseline(path, data, current):
    return path == "security/secrets-baseline.json" and data.replace(b"\r\n", b"\n") == current.replace(b"\r\n", b"\n")


def main():
    baseline_path = ROOT / "security/secrets-baseline.json"
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {"exceptions": []}
    accepted = {e["fingerprint"] for e in baseline["exceptions"] if e.get("reason")}
    refs = git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes", "refs/tags").decode().splitlines()
    refs.append("HEAD")  # Includes GitHub's checked-out PR merge commit.
    objects = git("rev-list", "--objects", *refs).decode().splitlines()
    manifest = (ROOT / "release/RELEASE_SOURCE_FILES.txt").read_text().splitlines()
    items = [("source:" + p, verified_digest_text((ROOT / p).read_bytes()) if p == DIGEST
              else (ROOT / p).read_bytes(), p) for p in manifest
             if p != "security/secrets-baseline.json"]
    verified_history = verified_history_metadata(refs)
    history_count = 0
    for line in objects:
        oid, _, path = line.partition(" ")
        if git("cat-file", "-t", oid).strip() == b"blob":
            history_count += 1
            data = git("cat-file", "blob", oid)
            if same_reviewed_baseline(path, data, baseline_path.read_bytes()):
                # Same reviewed baseline excluded from current scanning; other historical versions remain scanned.
                continue
            if path == DIGEST and oid in verified_history:
                data = verified_history[oid]
            items.append(("git:" + oid + ":" + path, data, path))
    findings = []
    unreadable = []
    with tempfile.TemporaryDirectory(prefix="hr-secret-scan-") as directory:
        export = Path(directory)
        # Prove the scanner actually traversed this export and detects new secrets.
        (export / "canary.txt").write_text('password = "' + secrets.token_urlsafe(32) + '"')
        mapping = {}
        for index, (location, data, path) in enumerate(items):
            try:
                content = text_content(data, path)
            except Exception:  # Any extraction failure fails closed without raw document diagnostics.
                unreadable.append(location)
                continue
            target = export / f"{index}.txt"
            target.write_text(content.replace("\r\n", "\n"), encoding="utf-8")
            mapping[target.name] = (location, hashlib.sha256(content.replace("\r\n", "\n").encode()).hexdigest())
        # Default detectors and filters; verification disabled (no provider traffic).
        scanner = ROOT / ".security-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        result = subprocess.run([str(scanner), "-m", "detect_secrets", "scan", "--all-files", "--no-verify",
                                 "--exclude-lines", r'^\s*--hash=sha256:[a-f0-9]{64}\s*\\?$',
                                 "--exclude-lines", r'^\s*"integrity": "sha(?:256|512)-[A-Za-z0-9+/=]+",?$',
                                 "."],
                                cwd=export, capture_output=True, timeout=300)
        if result.returncode:
            raise RuntimeError("Secret scanner failed; raw diagnostics withheld")
        scan = json.loads(result.stdout)
        assert any(Path(p).name == "canary.txt" for p in scan["results"]), "Secret scanner canary failed"
        for filename, entries in scan["results"].items():
            if Path(filename).name == "canary.txt":
                continue
            location, digest = mapping[Path(filename).name]
            for entry in entries:
                fingerprint = hashlib.sha256((digest + ":" + entry["type"] + ":" + entry["hashed_secret"]).encode()).hexdigest()
                findings.append({"fingerprint": fingerprint, "location": location,
                                 "line": entry["line_number"], "category": entry["type"]})
    new = [f for f in findings if f["fingerprint"] not in accepted]
    # Optional local review output has hashes/locations/categories only, never values.
    if "--review" in sys.argv:
        target = ROOT / ".local-dev/reports/secret-review.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(new, indent=2))
    for finding in new:
        print(finding["location"], "line", finding["line"], finding["category"])
    for location in unreadable:
        print("UNREVIEWED BINARY:", location)
    print(f"Secret scan: {len(manifest)} proposed files; {len(refs)} ref tips including HEAD; "
          f"{history_count} historical blobs; {len(findings)} findings; "
          f"{len(new)} unreviewed; {len(unreadable)} unreadable")
    return int(bool(new or unreadable))


if __name__ == "__main__":
    sys.exit(main())
