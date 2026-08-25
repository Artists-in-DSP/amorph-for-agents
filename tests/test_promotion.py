#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_external_context import DEFAULT_RELEASE, build
from scripts.promote_external_context import promote


class PromotionTests(unittest.TestCase):
    def test_promotion_copies_exact_visible_documents_and_is_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "public-context"
            self.assertEqual(0, build(DEFAULT_RELEASE, output_root, False))
            promote(output_root, DEFAULT_RELEASE)

            source_root = output_root / "v1" / DEFAULT_RELEASE
            stable_root = output_root / "v1" / "stable"
            archive_root = output_root / "v1" / "releases" / "20260824-a"
            stable_manifest = json.loads((stable_root / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(DEFAULT_RELEASE, stable_manifest["active_release"])
            self.assertEqual("v1/releases/20260824-a", stable_manifest["immutable_archive"])
            for record in stable_manifest["documents"]:
                for key in ("audit_path", "html_path"):
                    relative = Path(record[key])
                    self.assertEqual(
                        (source_root / relative).read_bytes(),
                        (stable_root / relative).read_bytes(),
                    )
                    self.assertEqual(
                        (source_root / relative).read_bytes(),
                        (archive_root / relative).read_bytes(),
                    )

            # Re-promoting the same immutable release is deterministic.
            promote(output_root, DEFAULT_RELEASE)
            self.assertEqual(DEFAULT_RELEASE, json.loads(
                (stable_root / "manifest.json").read_text(encoding="utf-8")
            )["active_release"])


if __name__ == "__main__":
    unittest.main()
