"""Fingerprint of everything a page shows (stored readings + site code), so the scheduled job only
rebuilds and deploys when something changed. Compared with the live site's /live.json.
Usage: python scripts/digest.py [--write]   (--write also writes public/live.json for the deploy)
"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
h = hashlib.sha256()
for f in sorted((ROOT / "data" / "lakes").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    d.pop("fetched", None)  # changes every run even when no reading changed
    h.update(f.name.encode()); h.update(json.dumps(d, sort_keys=True).encode())
code = [ROOT / "astro.config.mjs", ROOT / "package-lock.json", ROOT / "data" / "registry.json"]
for d in ("src", "public", "scripts"):
    code += [f for f in (ROOT / d).rglob("*") if f.is_file()]
for f in sorted(code, key=lambda f: f.relative_to(ROOT).as_posix()):
    rel = f.relative_to(ROOT).as_posix()
    if rel.startswith(("src/data/", "public/live.json")) or "__pycache__" in rel:
        continue
    h.update(rel.encode()); h.update(f.read_bytes().replace(b"\r\n", b"\n"))
digest = h.hexdigest()[:16]
if sys.argv[1:2] == ["--write"]:
    (ROOT / "public" / "live.json").write_text(json.dumps({"digest": digest, "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}), encoding="utf-8")
print(digest)
