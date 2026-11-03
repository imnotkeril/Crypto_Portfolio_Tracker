from pathlib import Path

from utils.disclaimer import DISCLAIMER

ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_disclaimer_text():
    assert "Not investment advice" in DISCLAIMER
    assert "can lose all capital" in DISCLAIMER


def test_readme_contains_disclaimer():
    assert DISCLAIMER in _read("README.md")


def test_main_and_backtest_render_disclaimer():
    for rel in ("main.py", "pages/backtest.py"):
        src = _read(rel)
        assert "from utils.disclaimer import DISCLAIMER" in src, rel
        assert "(DISCLAIMER)" in src, rel
    assert _read("pages/backtest.py").count("(DISCLAIMER)") >= 3  # top + both result blocks
