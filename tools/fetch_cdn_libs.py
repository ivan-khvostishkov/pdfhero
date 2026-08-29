"""
fetch_cdn_libs.py — Download pinned CDN libraries to local disk and record SHA-256 hashes.

Usage (from project root):
    python tools/fetch_cdn_libs.py

Requires only Python 3.8+ stdlib — no pip installs needed.
"""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Library manifest ──────────────────────────────────────────────────────────
# Each entry mirrors the CDN assets referenced by PDFhero.html and sw.js.
# Update 'url' and 'local_path' whenever a library version is bumped.
#
# NOTE: pdfcpu.wasm (v0.15.0) is NOT listed here — it is served as a local
# file alongside PDFhero.html and does not have a CDN URL.
LIBRARIES = [
    {
        "name": "PDF.js",
        "url": "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs",
        "local_path": "vendor/pdf.js/pdf.min.mjs",
    },
    {
        "name": "PDF.js Worker",
        "url": "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs",
        "local_path": "vendor/pdf.js/pdf.worker.min.mjs",
    },
    {
        "name": "pdf-lib",
        "url": "https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js",
        "local_path": "vendor/pdf-lib/pdf-lib.min.js",
    },
]

VENDOR_MANIFEST = Path("vendor/manifest.json")


# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256_of_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at *path*."""
    return sha256_of_bytes(path.read_bytes())


def load_manifest() -> dict:
    """Load vendor/manifest.json; return an empty dict if it doesn't exist."""
    if VENDOR_MANIFEST.exists():
        try:
            return json.loads(VENDOR_MANIFEST.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_manifest(data: dict) -> None:
    """Write *data* to vendor/manifest.json (pretty-printed)."""
    VENDOR_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    VENDOR_MANIFEST.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def download_bytes(url: str) -> bytes:
    """Download *url* and return the response body as bytes."""
    # urllib.request.urlretrieve writes to a temp file; using urlopen is simpler
    # for in-memory bytes and avoids leaving temp files behind on error.
    with urllib.request.urlopen(url) as response:  # noqa: S310 — URL comes from LIBRARIES constant
        return response.read()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    manifest = load_manifest()
    fetched = 0
    changed = 0

    for lib in LIBRARIES:
        name = lib["name"]
        url = lib["url"]
        local_path = Path(lib["local_path"])

        print(f"Fetching {name} …", end=" ", flush=True)

        # Download
        data = download_bytes(url)
        current_sha256 = sha256_of_bytes(data)

        # Write to disk (always — keeps the file fresh)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

        # Compare against previously recorded hash
        previous_entry = manifest.get(lib["local_path"])
        previous_sha256 = previous_entry.get("sha256") if previous_entry else None

        if previous_sha256 is None:
            # First time this file has been fetched
            print(f"[NEW] saved to {local_path}")
        elif previous_sha256 == current_sha256:
            print(f"[OK] {name} — unchanged")
        else:
            print(
                f"[CHANGED] {name} — SHA-256 mismatch!\n"
                f"  Previous: {previous_sha256}\n"
                f"  Current:  {current_sha256}"
            )
            changed += 1

        # Update manifest entry
        manifest[lib["local_path"]] = {
            "name": name,
            "url": url,
            "local_path": lib["local_path"],
            "sha256": current_sha256,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        fetched += 1

    save_manifest(manifest)
    print(f"\nFetched {fetched} files. {changed} changed. Saved to vendor/")


if __name__ == "__main__":
    main()
