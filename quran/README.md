# Quran translation mirror

This directory hosts the English Quran translation snapshot used by the English flavor of Dzikir Pagi Petang / Daily Dhikr & Prayer.

## Rowwad English translation

- Translation key: `english_rwwad`
- Publisher: Rowwad Translation Center
- Upstream source: QuranEnc.com
- Source page: https://quranenc.com/en/browse/english_rwwad
- Data snapshot: `english_rwwad.json`
- Lightweight manifest: `english_rwwad.meta.json`

The translation and footnote text is mirrored from QuranEnc without editorial modification. Source/version metadata is retained in the generated files. The snapshot generator validates that the data contains 114 surahs and 6,236 ayahs before publishing it.

## Refreshing the snapshot

`scripts/sync_rowwad.py` fetches the current `english_rwwad` dataset from the official QuranEnc API, validates it, and writes the data + manifest. `.github/workflows/sync-rowwad.yml` runs the generator and commits refreshed generated files.

The application should use this repository's GitHub Pages endpoint as its remote mirror and persist a validated snapshot locally. A translation-network failure must never prevent the Arabic mushaf from being displayed.
