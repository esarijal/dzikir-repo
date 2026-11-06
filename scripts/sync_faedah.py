#!/usr/bin/env python3
# Mirror of the faedah Google Sheet (CSV export) as a validated JSON bundle.
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_URL = "FAEDAH_SHEET_CSV_URL"
OUT_PATH = Path("faedah/faedah.id.json")
META_PATH = Path("faedah/faedah.id.meta.json")
SCHEMA = 1
MAX_TEXT = 280
MIN_UMUM = 30
ID_RE = re.compile(r"^f\d{4}$")
SEASONS = {"umum", "ramadhan", "10_dzulhijjah", "asyura", "syaban"}
COLUMNS = {
    "id": "id",
    "teks_id": "text",
    "ustadz": "author",
    "sumber_judul": "source",
    "musim": "season",
}
USER_AGENT = "DzikirPagiPetang-Faedah-Mirror/1.0 (+https://github.com/esarijal/dzikir-repo)"


def utf16_len(text: str) -> int:
    """Length in UTF-16 code units, identical to Dart's String.length."""
    return len(text.encode("utf-16-le")) // 2


def parse_csv(raw: bytes) -> list:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"CSV kehilangan kolom: {', '.join(missing)}")
    rows = []
    for rec in reader:
        row = {dst: (rec.get(src) or "").strip() for src, dst in COLUMNS.items()}
        if not any(row.values()):
            continue  # blank line
        rows.append(row)
    return rows


def validate(rows: list) -> list:
    """Returns cleaned, id-sorted rows; raises ValueError listing all violations."""
    errors = []
    seen = set()
    clean = []
    for n, raw in enumerate(rows, start=1):
        rid = str(raw.get("id", "")).strip()
        label = rid or f"baris {n}"
        text = str(raw.get("text", "")).strip()
        author = str(raw.get("author", "")).strip()
        source = str(raw.get("source", "")).strip()
        season = str(raw.get("season", "")).strip()
        if not ID_RE.match(rid):
            errors.append(f'{label}: id "{rid}" tidak berformat fNNNN')
        elif rid in seen:
            errors.append(f"{label}: id ganda")
        seen.add(rid)
        if not text or utf16_len(text) > MAX_TEXT:
            errors.append(f"{label}: teks harus 1-{MAX_TEXT} karakter (UTF-16)")
        if not author:
            errors.append(f"{label}: author kosong")
        if not source:
            errors.append(f"{label}: source kosong")
        if season not in SEASONS:
            errors.append(f'{label}: musim tidak dikenal "{season}"')
        clean.append(
            {"id": rid, "text": text, "author": author, "source": source, "season": season}
        )
    umum = sum(1 for r in clean if r["season"] == "umum")
    if umum < MIN_UMUM:
        errors.append(f"hanya {umum} item umum, minimal {MIN_UMUM}")
    if errors:
        raise ValueError("Validasi faedah gagal:\n- " + "\n- ".join(errors))
    return sorted(clean, key=lambda r: r["id"])


def build(rows: list, previous, now: datetime):
    items = sorted(
        (
            {k: r[k] for k in ("id", "text", "author", "source", "season")}
            for r in rows
        ),
        key=lambda r: r["id"],
    )
    version = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if previous and previous.get("items") == items:
        version = previous.get("meta", {}).get("version") or version
    meta = {"schema": SCHEMA, "version": version, "count": len(items)}
    return {"meta": dict(meta), "items": items}, meta


def _atomic_write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def main():
    url = os.environ.get(ENV_URL, "").strip()
    if not url:
        sys.exit(f"Galat: env {ENV_URL} kosong atau tidak diset")
    try:
        rows = validate(parse_csv(_fetch(url)))
    except ValueError as exc:
        sys.exit(str(exc))
    previous = None
    if OUT_PATH.exists():
        try:
            previous = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = None
    bundle, meta = build(rows, previous, datetime.now(timezone.utc))
    _atomic_write(OUT_PATH, bundle)
    _atomic_write(META_PATH, meta)
    print(f"wrote {OUT_PATH}: version={meta['version']} count={meta['count']}")


if __name__ == "__main__":
    main()
