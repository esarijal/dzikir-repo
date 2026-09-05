#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TRANSLATION_KEY = "english_rwwad"
BASE_URL = "https://quranenc.com/api/v1"
OUT_PATH = Path("quran/english_rwwad.json")
EXPECTED_SURAHS = 114
EXPECTED_AYAHS = 6236
USER_AGENT = "DzikirPagiPetang-Rowwad-Snapshot/1.0 (+https://github.com/esarijal/dzikir-repo)"


def _get_json(url: str, attempts: int = 7):
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"HTTP {status} for {url}")
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = min(30, 2 ** attempt)
            print(f"retry {attempt + 1}/{attempts - 1} after {exc}; sleeping {delay}s")
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def _translation_metadata():
    raw = _get_json(f"{BASE_URL}/translations/list/en?localization=en")
    items = raw if isinstance(raw, list) else raw.get("translations") or raw.get("result") or raw.get("data") or []
    for item in items:
        if isinstance(item, dict) and item.get("key") == TRANSLATION_KEY:
            return item
    raise RuntimeError(f"Translation key {TRANSLATION_KEY!r} not found in QuranEnc translation list")


def _rows_for_surah(surah: int):
    raw = _get_json(f"{BASE_URL}/translation/sura/{TRANSLATION_KEY}/{surah}")
    rows = raw if isinstance(raw, list) else raw.get("result") or raw.get("data") or raw.get("translations")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"Unexpected/empty response for surah {surah}")

    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"Non-object row in surah {surah}")
        # Preserve QuranEnc content fields exactly as delivered by the API.
        normalized.append({
            "sura": row.get("sura"),
            "aya": row.get("aya"),
            "translation": row.get("translation"),
            "footnotes": row.get("footnotes"),
        })
    return normalized


def main():
    metadata = _translation_metadata()
    surahs = {}
    total_ayahs = 0

    for surah in range(1, EXPECTED_SURAHS + 1):
        rows = _rows_for_surah(surah)
        surahs[str(surah)] = rows
        total_ayahs += len(rows)
        print(f"surah {surah:03d}: {len(rows)} ayahs")
        time.sleep(0.10)

    if len(surahs) != EXPECTED_SURAHS:
        raise RuntimeError(f"Expected {EXPECTED_SURAHS} surahs, got {len(surahs)}")
    if total_ayahs != EXPECTED_AYAHS:
        raise RuntimeError(f"Expected {EXPECTED_AYAHS} ayahs, got {total_ayahs}")

    payload = {
        "meta": {
            "translation_key": TRANSLATION_KEY,
            "publisher": "Rowwad Translation Center",
            "source": "QuranEnc.com",
            "source_url": "https://quranenc.com/en/browse/english_rwwad",
            "version": metadata.get("version"),
            "last_update": metadata.get("last_update"),
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "surah_count": EXPECTED_SURAHS,
            "ayah_count": total_ayahs,
        },
        "surahs": surahs,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, OUT_PATH)
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
