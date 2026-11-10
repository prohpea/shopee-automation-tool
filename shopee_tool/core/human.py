"""
Shopee Automation Tool - Human Behavior Simulation.
Simulates natural pauses, randomized keystroke latencies, and human-like scrolling.
"""

import asyncio
import random
from typing import Optional, Tuple
from playwright.async_api import Page
from .config import settings


async def sleep_random(
    min_seconds: Optional[float] = None, max_seconds: Optional[float] = None
) -> float:
    """
    Sleeps for a random duration between min_seconds and max_seconds.
    Defaults come from MIN_ACTION_DELAY / MAX_ACTION_DELAY.
    """
    low = settings.min_delay if min_seconds is None else min_seconds
    high = settings.max_delay if max_seconds is None else max_seconds
    actual = random.uniform(low, high)
    await asyncio.sleep(actual)
    return actual


async def human_scroll(
    page: Page,
    steps: int = 5,
    min_scroll_delta: int = 200,
    max_scroll_delta: int = 500,
    delay_between_steps: Tuple[float, float] = (0.4, 0.9),
) -> None:
    """
    Scrolls down progressively with variable speed, mimicking a user browsing items.
    """
    for _ in range(steps):
        scroll_amount = random.randint(min_scroll_delta, max_scroll_delta)
        # Random micro reverse scrolling (10% chance) mimicking checking previous item
        if random.random() < 0.1:
            scroll_amount = -random.randint(50, 150)

        await page.mouse.wheel(0, scroll_amount)
        step_delay = random.uniform(*delay_between_steps)
        await asyncio.sleep(step_delay)

