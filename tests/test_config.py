"""
Unit tests for configuration and regional settings.
"""

from pathlib import Path
from shopee_tool.core.config import Settings, ShopeeRegionalConfig


def test_default_config():
    cfg = Settings()
    assert cfg.region in ("vn", "sg", "my", "th", "id", "ph", "tw")
    assert cfg.base_url.startswith("https://shopee.")
    assert cfg.nav_timeout_ms > 0
    assert cfg.min_delay < cfg.max_delay


def test_regional_domains():
    for region, domain in ShopeeRegionalConfig.DOMAINS.items():
        assert domain.startswith("https://shopee")
        cfg = Settings(region=region)
        assert cfg.base_url == domain
        assert region in cfg.login_url or "shopee" in cfg.login_url


def test_session_paths(tmp_path: Path):
    cfg = Settings(root_dir=tmp_path, sessions_dir=tmp_path / "sessions")
    p = cfg.get_session_path("test_account")
    assert p.name == "test_account.json"
    assert p.parent.exists()
