"""
Shopee Automation Tool - Configuration Module.
Loads environment variables and provides typed settings.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class ShopeeRegionalConfig:
    """Regional Shopee domains and the paths appended to them."""

    DOMAINS: Dict[str, str] = {
        "vn": "https://shopee.vn",
        "sg": "https://shopee.sg",
        "my": "https://shopee.com.my",
        "th": "https://shopee.co.th",
        "id": "https://shopee.co.id",
        "ph": "https://shopee.ph",
        "tw": "https://shopee.tw",
    }

    LOGIN_PATH = "/buyer/login"
    COINS_PATH = "/shopee-coins"

    # Region-specific voucher hub paths ('vn' uses the Vietnamese slug).
    VOUCHERS_PATH: Dict[str, str] = {
        "vn": "/m/ma-giam-gia",
    }
    DEFAULT_VOUCHERS_PATH = "/m/vouchers"

    @classmethod
    def domain(cls, region: str) -> str:
        return cls.DOMAINS.get(region, cls.DOMAINS["vn"])

    @classmethod
    def vouchers_path(cls, region: str) -> str:
        return cls.VOUCHERS_PATH.get(region, cls.DEFAULT_VOUCHERS_PATH)


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("true", "1", "yes")


class Settings(BaseModel):
    """Application configuration settings."""

    # Region
    region: str = Field(default_factory=lambda: os.getenv("SHOPEE_REGION", "vn").lower())

    # Automation / Browser Settings
    headless: bool = Field(default_factory=lambda: _env_flag("HEADLESS"))
    nav_timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("NAV_TIMEOUT_MS", "45000"))
    )

    # Delays (seconds)
    min_delay: float = Field(
        default_factory=lambda: float(os.getenv("MIN_ACTION_DELAY", "1.5"))
    )
    max_delay: float = Field(
        default_factory=lambda: float(os.getenv("MAX_ACTION_DELAY", "3.5"))
    )

    # Sessions
    default_session_name: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_SESSION", "default")
    )

    # Anti-Detection
    stealth_mode: bool = Field(default_factory=lambda: _env_flag("STEALTH_MODE", "true"))
    custom_user_agent: Optional[str] = Field(
        default_factory=lambda: os.getenv("USER_AGENT") or None
    )

    # Proxy Configuration
    proxy_server: Optional[str] = Field(
        default_factory=lambda: os.getenv("PROXY_SERVER") or None
    )
    proxy_username: Optional[str] = Field(
        default_factory=lambda: os.getenv("PROXY_USERNAME") or None
    )
    proxy_password: Optional[str] = Field(
        default_factory=lambda: os.getenv("PROXY_PASSWORD") or None
    )

    # Directories
    root_dir: Path = PROJECT_ROOT
    sessions_dir: Path = PROJECT_ROOT / "data" / "sessions"
    profiles_dir: Path = PROJECT_ROOT / "data" / "profiles"
    exports_dir: Path = PROJECT_ROOT / "data" / "exports"
    logs_dir: Path = PROJECT_ROOT / "logs"

    @property
    def base_url(self) -> str:
        return ShopeeRegionalConfig.domain(self.region)

    @property
    def login_url(self) -> str:
        return f"{self.base_url}{ShopeeRegionalConfig.LOGIN_PATH}"

    @property
    def coins_url(self) -> str:
        return f"{self.base_url}{ShopeeRegionalConfig.COINS_PATH}"

    @property
    def vouchers_url(self) -> str:
        return f"{self.base_url}{ShopeeRegionalConfig.vouchers_path(self.region)}"

    def get_session_path(self, session_name: Optional[str] = None) -> Path:
        name = session_name or self.default_session_name
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        return self.sessions_dir / f"{name}.json"

    def get_profile_dir(self, profile_name: Optional[str] = None) -> Path:
        name = profile_name or self.default_session_name
        p_dir = self.profiles_dir / name
        p_dir.mkdir(parents=True, exist_ok=True)
        return p_dir


settings = Settings()
