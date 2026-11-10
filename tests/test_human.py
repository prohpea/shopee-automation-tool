"""
Unit tests for human behavior delays.
"""

import asyncio
from shopee_tool.core.human import sleep_random


def test_sleep_random_bounds():
    min_s = 0.05
    max_s = 0.15
    duration = asyncio.run(sleep_random(min_s, max_s))
    assert min_s <= duration <= max_s


def test_sleep_random_defaults_follow_settings():
    """The no-argument default must honour MIN_ACTION_DELAY / MAX_ACTION_DELAY."""
    from shopee_tool.core.config import settings

    duration = asyncio.run(sleep_random())
    assert settings.min_delay <= duration <= settings.max_delay
