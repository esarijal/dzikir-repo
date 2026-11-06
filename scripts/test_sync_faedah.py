import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sync_faedah  # noqa: E402


def make_rows(n=30, season="umum"):
    return [
        {
            "id": f"f{i:04d}",
            "text": f"teks uji {i}",
            "author": "ustadz uji",
            "source": "sumber uji",
            "season": season,
        }
        for i in range(1, n + 1)
    ]


NOW = datetime(2026, 11, 6, 20, 0, 0, tzinfo=timezone.utc)


class SyncFaedahTest(unittest.TestCase):
    def test_valid_rows_build_bundle(self):
        rows = list(reversed(make_rows()))
        rows.append({**make_rows(1)[0], "id": "f0100", "season": "10_dzulhijjah"})
        bundle, meta = sync_faedah.build(sync_faedah.validate(rows), None, NOW)
        self.assertEqual(bundle["meta"], meta)
        self.assertEqual(meta, {"schema": 1, "version": "2026-11-06T20:00:00Z", "count": 31})
        ids = [i["id"] for i in bundle["items"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(
            set(bundle["items"][0]), {"id", "text", "author", "source", "season"}
        )

    def test_duplicate_id_rejected(self):
        rows = make_rows()
        rows[1]["id"] = rows[0]["id"]
        with self.assertRaises(ValueError) as cm:
            sync_faedah.validate(rows)
        self.assertIn("f0001", str(cm.exception))

    def test_text_over_280_rejected(self):
        rows = make_rows()
        rows[0]["text"] = "a" * 281
        with self.assertRaises(ValueError):
            sync_faedah.validate(rows)

    def test_text_280_accepted_and_trimmed(self):
        rows = make_rows()
        rows[0]["text"] = "  " + "a" * 280 + "  "
        out = sync_faedah.validate(rows)
        self.assertEqual(len(out[0]["text"]), 280)

    def test_length_counts_utf16_units(self):
        # Emoji = 1 code point but 2 UTF-16 units (Dart String.length == 2).
        rows = make_rows()
        rows[0]["text"] = "a" * 278 + "\U0001F600"  # 280 units: ok
        sync_faedah.validate(rows)
        rows[0]["text"] = "a" * 279 + "\U0001F600"  # 281 units, 280 code points
        with self.assertRaises(ValueError):
            sync_faedah.validate(rows)

    def test_unknown_season_rejected(self):
        rows = make_rows()
        rows[0]["season"] = "musim_aneh"
        with self.assertRaises(ValueError):
            sync_faedah.validate(rows)

    def test_fewer_than_30_umum_rejected(self):
        with self.assertRaises(ValueError):
            sync_faedah.validate(make_rows(29))

    def test_bad_id_and_empty_fields_all_reported(self):
        rows = make_rows()
        rows[0]["id"] = "x1"
        rows[1]["author"] = " "
        rows[2]["source"] = ""
        rows[3]["text"] = "  "
        with self.assertRaises(ValueError) as cm:
            sync_faedah.validate(rows)
        msg = str(cm.exception)
        self.assertIn("x1", msg)
        self.assertIn("f0002", msg)
        self.assertIn("f0003", msg)
        self.assertIn("f0004", msg)

    def test_same_items_keep_version(self):
        bundle, _ = sync_faedah.build(make_rows(), None, NOW)
        later = datetime(2026, 11, 7, 20, 0, 0, tzinfo=timezone.utc)
        again, meta = sync_faedah.build(make_rows(), bundle, later)
        self.assertEqual(meta["version"], "2026-11-06T20:00:00Z")
        self.assertEqual(again, bundle)

    def test_changed_items_new_version(self):
        bundle, _ = sync_faedah.build(make_rows(), None, NOW)
        rows = make_rows()
        rows[0]["text"] = "teks uji berubah"
        later = datetime(2026, 11, 7, 20, 0, 0, tzinfo=timezone.utc)
        _, meta = sync_faedah.build(rows, bundle, later)
        self.assertEqual(meta["version"], "2026-11-07T20:00:00Z")

    def test_parse_csv_maps_columns_and_strips_bom(self):
        raw = "﻿id,teks_id,ustadz,sumber_judul,musim\nf0001,  teks uji 1 ,U,S,umum\n"
        rows = sync_faedah.parse_csv(raw.encode("utf-8"))
        self.assertEqual(
            rows,
            [{"id": "f0001", "text": "teks uji 1", "author": "U", "source": "S", "season": "umum"}],
        )

    def test_missing_env_exits_nonzero(self):
        os.environ.pop("FAEDAH_SHEET_CSV_URL", None)
        with self.assertRaises(SystemExit) as cm:
            sync_faedah.main()
        self.assertNotEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
