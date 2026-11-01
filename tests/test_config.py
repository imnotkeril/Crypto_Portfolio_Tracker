import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_streamlit_server_is_local_only():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["server"]["address"] == "127.0.0.1"
    assert cfg["server"]["allowedHosts"] == ["localhost", "127.0.0.1"]
