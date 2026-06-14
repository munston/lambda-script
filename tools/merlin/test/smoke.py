from __future__ import annotations

from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from merlin.detector import scan_path

def test_detects_placeholder_return() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("def f():\n    return None\n", encoding="utf-8")
        report = scan_path(root)
        assert report.scanned_files == 1
        assert report.issue_count == 1
        assert report.issues[0].rule == "weak-return-none"

def test_ignores_non_source_file() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "notes.txt"
        target.write_text("mock placeholder\n", encoding="utf-8")
        report = scan_path(root)
        assert report.scanned_files == 0
        assert report.issue_count == 0

def main() -> int:
    test_detects_placeholder_return()
    test_ignores_non_source_file()
    print("merlin smoke passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
