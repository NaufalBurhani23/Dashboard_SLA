from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ALLOWED_TEXT = {"H5", "H6", "H8", "H9"}  # only legacy period-reference metadata, not source data columns


def test_sla_calculators_do_not_reference_source_excel_column_letters():
    forbidden_tokens = ["P/", "Q/", "X/", "Y/", "Z/", "AH/", "AJ/", "AK/", "AD=", "AD<", "AD>"]
    for path in (APP_ROOT / "sla").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text, f"{token} masih muncul di {path}"
