import sys
import types

from utils import assets


class _Ex:
    def load_markets(self):
        return {"BTC/USDT": {"active": True}, "ETH/USDT": {"active": True},
                "USDC/USDT": {"active": True}, "BTC/EUR": {"active": True}}


def _patch(monkeypatch, tmp_path):
    cache = tmp_path / "cache" / "assets.json"
    monkeypatch.setattr(assets, "ASSETS_CACHE_FILE", str(cache))
    mod = types.ModuleType("utils.price_fetcher")
    mod._get_ccxt = lambda: (None, _Ex())
    monkeypatch.setitem(sys.modules, "utils.price_fetcher", mod)


def test_usdt_offered_on_live_and_cached_paths(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    live = assets.get_available_assets(use_cache=False)
    assert "USDT" in live and {"BTC", "ETH", "USDC"} <= set(live)
    assert live.count("USDT") == 1
    cached = assets.get_available_assets()  # cache written by the live call
    assert "USDT" in cached and cached.count("USDT") == 1


def test_usdt_offered_on_fallback_path(monkeypatch, tmp_path):
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr(_Ex, "load_markets", lambda self: (_ for _ in ()).throw(RuntimeError("down")))
    out = assets.get_available_assets(use_cache=False)
    assert out.count("USDT") == 1
