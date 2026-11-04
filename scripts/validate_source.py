"""Validate selected source paths, Markdown links and content digest without Git writes."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "release/RELEASE_SOURCE_FILES.txt"
DIGEST = "release/RELEASE_SOURCE_DIGEST.json"


def selected_paths():
    names = (ROOT / MANIFEST).read_text(encoding="utf-8").splitlines()
    if names != sorted(set(names)):
        raise ValueError("Manifest must be sorted with no duplicate paths")
    for name in names:
        path = ROOT / name
        if (not name or "\\" in name or Path(name).is_absolute()
                or ".." in Path(name).parts or not path.resolve().is_relative_to(ROOT)
                or not path.is_file() or path.is_symlink()):
            raise ValueError(f"Invalid selected path: {name}")
        if any(p in {".local-dev", ".release-work", "node_modules", ".next", "uploads"}
               for p in Path(name).parts):
            raise ValueError(f"Private/generated path selected: {name}")
    return names


def digest_for(names):
    rows = []
    for name in names:
        if name == DIGEST:
            continue  # Included in export, but cannot hash itself.
        data = (ROOT / name).read_bytes()
        if Path(name).suffix not in {".pdf", ".docx", ".png"}:
            # Git may change text line endings at checkout (core.autocrlf).
            # Preserve every other byte and hash binary fixtures unchanged.
            data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
        rows.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    aggregate = "".join(f"{row['sha256']}  {row['path']}\n" for row in rows)
    return {"format": "sha256-lf-text-path-lines-v2", "count": len(rows),
            "digest": hashlib.sha256(aggregate.encode()).hexdigest(), "files": rows}


def anchors(text):
    result = set()
    counts = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        result.add(slug + (f"-{count}" if count else ""))
        counts[slug] = count + 1
    result.update(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', text))
    return result


def validate_links(names):
    selected = set(names)
    count = 0
    for name in names:
        if not name.endswith(".md"):
            continue
        text = (ROOT / name).read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.split(' "', 1)[0].strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            path = ((ROOT / name).parent / unquote(url.path)).resolve() if url.path else ROOT / name
            if not path.is_relative_to(ROOT):
                raise ValueError(f"Link escapes source: {name}: {target}")
            relative = path.relative_to(ROOT).as_posix()
            if relative not in selected:
                raise ValueError(f"Link not in selected source: {name}: {target}")
            if url.fragment and path.suffix == ".md" and unquote(url.fragment) not in anchors(path.read_text(encoding="utf-8")):
                raise ValueError(f"Missing anchor: {name}: {target}")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh digest for already reviewed manifest")
    parser.add_argument("--reconcile", action="store_true", help="Require every existing nonignored Git-visible file in manifest")
    args = parser.parse_args()
    names = selected_paths()
    count = validate_links(names)
    if args.reconcile:
        output = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
        visible = {n for n in output.decode().split("\0") if n and (ROOT / n).is_file()}
        if visible != set(names):
            raise ValueError(f"Manifest mismatch: extra={sorted(visible-set(names))}; missing={sorted(set(names)-visible)}")
    expected = digest_for(names)
    if args.refresh:
        (ROOT / DIGEST).write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    elif json.loads((ROOT / DIGEST).read_text(encoding="utf-8")) != expected:
        raise ValueError("Selected source changed; review changes before refreshing digest")
    print(f"PASS: {len(names)} selected files; {count} local links/anchors; digest verified")


if __name__ == "__main__":
    main()
