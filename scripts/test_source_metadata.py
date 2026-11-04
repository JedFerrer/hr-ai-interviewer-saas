"""Regression checks for the narrowly validated current-source hash filtering."""
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import check_secrets
import validate_source


class DigestFilteringTests(unittest.TestCase):
    def setUp(self):
        self.document = {"format": "sha256-path-lines-v1", "count": 1,
                         "digest": "a" * 64,
                         "files": [{"path": "public.py", "size": 4, "sha256": "b" * 64}]}

    def filter(self, document):
        with patch.object(check_secrets, "selected_paths", return_value=["public.py"]), \
                patch.object(check_secrets, "digest_for", return_value=self.document):
            return json.loads(check_secrets.verified_digest_text(json.dumps(document).encode()))

    def test_only_verified_hashes_are_removed_and_paths_remain(self):
        output = self.filter(self.document)
        self.assertEqual(output["files"][0]["path"], "public.py")
        self.assertEqual(output["files"][0]["sha256"], "verified-sha256")
        self.assertEqual(output["digest"], "verified-sha256")

    def test_stale_or_injected_metadata_fails(self):
        for document in ({**self.document, "digest": "changed"},
                         {**self.document, "unexpected": "not permitted"}):
            with self.assertRaises(ValueError):
                self.filter(document)

    def test_historical_digest_is_scanned_unmodified(self):
        raw = json.dumps(self.document).encode()
        self.assertEqual(check_secrets.text_content(raw, check_secrets.DIGEST), raw.decode())

    def test_checkout_line_endings_are_stable_but_binary_bytes_are_exact(self):
        with tempfile.TemporaryDirectory(prefix="hr-source-metadata-") as directory:
            root = Path(directory)
            with patch.object(validate_source, "ROOT", root):
                (root / "source.py").write_bytes(b"first\nsecond\n")
                before = validate_source.digest_for(["source.py"])
                (root / "source.py").write_bytes(b"first\r\nsecond\r\n")
                self.assertEqual(before, validate_source.digest_for(["source.py"]))
                (root / "fixture.png").write_bytes(b"binary\n")
                before = validate_source.digest_for(["fixture.png"])
                (root / "fixture.png").write_bytes(b"binary\r\n")
                self.assertNotEqual(before, validate_source.digest_for(["fixture.png"]))


if __name__ == "__main__":
    unittest.main()
