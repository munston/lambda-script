from __future__ import annotations

from pathlib import Path
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from merlin.detector import report_to_payload, scan_path

def test_detects_placeholder_return() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("def f():\n    return None\n", encoding="utf-8")
        report = scan_path(root)
        assert report.scanned_files == 1
        assert report.issue_count == 1
        assert report.error_count == 1
        assert report.warning_count == 0
        assert report.passed is False
        assert report.issues[0].rule == "weak-return-none"
        assert report.issues[0].gear == "return-substance"
        assert report.issues[0].fingerprint
        assert report.files[0].sha256

def test_ignores_non_source_file() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "notes.txt"
        target.write_text("mock placeholder\n", encoding="utf-8")
        report = scan_path(root)
        assert report.scanned_files == 0
        assert report.issue_count == 0
        assert report.passed is True

def test_mock_language_is_warning() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("# placeholder for parser edge case\nvalue = 1\n", encoding="utf-8")
        report = scan_path(root)
        assert report.issue_count == 1
        assert report.error_count == 0
        assert report.warning_count == 1
        assert report.passed is True
        assert report.issues[0].gear == "semantic-substance"

def test_inline_suppression() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("def f():\n    return None  # merlin: allow return-substance\n", encoding="utf-8")
        report = scan_path(root)
        assert report.issue_count == 0
        assert report.error_count == 0
        assert report.suppressed_count == 1
        assert report.passed is True
        assert report.suppressed_issues[0].source == "inline"

def test_configured_suppression() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("# placeholder vocabulary in detector fixture\nvalue = 1\n", encoding="utf-8")
        suppressions = root / "suppressions.json"
        suppressions.write_text(json.dumps({
            "format": "LS_MERLIN_SUPPRESSIONS_V1",
            "suppressions": [
                {
                    "path": "sample.py",
                    "rule": "mock-language",
                    "reason": "fixture intentionally uses detector vocabulary"
                }
            ]
        }), encoding="utf-8")
        report = scan_path(root, suppression_path=suppressions)
        assert report.issue_count == 0
        assert report.warning_count == 0
        assert report.suppressed_count == 1
        assert report.suppressed_issues[0].source == "suppressions"

def test_report_payload_can_hide_suppressed() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target = root / "sample.py"
        target.write_text("def f():\n    return None  # merlin: allow weak-return-none\n", encoding="utf-8")
        report = scan_path(root)
        visible = report_to_payload(report, include_suppressed=True)
        hidden = report_to_payload(report, include_suppressed=False)
        assert "suppressed_issues" in visible
        assert "suppressed_issues" not in hidden

def main() -> int:
    test_detects_placeholder_return()
    test_ignores_non_source_file()
    test_mock_language_is_warning()
    test_inline_suppression()
    test_configured_suppression()
    test_report_payload_can_hide_suppressed()
    print("merlin smoke passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
