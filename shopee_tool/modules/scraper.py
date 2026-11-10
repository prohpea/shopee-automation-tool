"""
Shopee Automation Tool - Product & Search Scraper.
Extracts product lists, search results, pricing, and details via API interception & DOM parsing.
"""

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from playwright.async_api import Page, Response
from ..core.browser import BrowserManager
from ..core.config import settings
from ..core.human import sleep_random, human_scroll
from ..modules.fast_voucher_hunter import is_cdp_port_active
from ..utils.logger import logger


def _scale_price(raw: Any) -> float:
    """
    Converts a Shopee API price to currency units.

    Shopee's v4 API returns prices as integers in units of 1/100000 (for example
    15_000_000_000 -> 150,000 VND). Always dividing is correct; the previous
    "only divide when > 100000" heuristic silently returned raw units for cheap
    items (an 0.80 SGD listing stayed 80000).
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return value / 100000 if value > 0 else 0.0


def parse_shopee_api_items(api_data: Dict[str, Any], base_url: str = "https://shopee.vn") -> List[Dict[str, Any]]:
    """
    Parses raw JSON data intercepted from Shopee's internal search API.
    Handles both legacy and v4 search item response structures.
    """
    results: List[Dict[str, Any]] = []
    items = api_data.get("items") or api_data.get("item_cards") or []

    for entry in items:
        # Some responses nest under 'item_basic'
        item = entry.get("item_basic", entry)
        if not item or not isinstance(item, dict):
            continue

        item_id = item.get("itemid")
        shop_id = item.get("shopid")
        name = item.get("name") or item.get("title") or ""

        price = _scale_price(item.get("price", 0))
        min_price = _scale_price(item.get("price_min", 0))
        max_price = _scale_price(item.get("price_max", 0))

        historical_sold = item.get("historical_sold", 0) or item.get("sold", 0)
        rating_star = round(item.get("item_rating", {}).get("rating_star", 0.0), 1) if isinstance(item.get("item_rating"), dict) else 0.0
        discount = item.get("discount") or ""
        # tier_variations holds option groups ("Màu sắc", "Kích cỡ"), never a
        # location, so it is not a shop_location fallback.
        shop_location = item.get("shop_location") or ""
        image_id = item.get("image") or ""
        image_url = f"https://down-vn.img.susercontent.com/file/{image_id}" if image_id else ""

        # Construct web URL
        clean_name = urllib.parse.quote(name.replace(" ", "-").lower()[:60])
        product_url = f"{base_url}/{clean_name}-i.{shop_id}.{item_id}" if shop_id and item_id else ""

        results.append({
            "item_id": item_id,
            "shop_id": shop_id,
            "name": name,
            "price": price,
            "min_price": min_price,
            "max_price": max_price,
            "historical_sold": historical_sold,
            "rating_star": rating_star,
            "discount": discount,
            "shop_location": shop_location,
            "image_url": image_url,
            "product_url": product_url,
        })

    return results


def parse_price_string(price_str: str) -> float:
    """
    Cleans a currency string (e.g. '₫150.000', '150.000 đ', '$15.50') to float.

    A bare dot/comma group of exactly three digits is a thousands separator;
    otherwise it is a decimal point ('19.99'). Both present means the rightmost
    one is the decimal separator.
    """
    if not price_str:
        return 0.0
    cleaned = re.sub(r"[₫đĐ$\s]", "", price_str).strip()
    if not cleaned:
        return 0.0

    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(".") > cleaned.rfind(","):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned or "," in cleaned:
        sep = "." if "." in cleaned else ","
        parts = cleaned.split(sep)
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):
            cleaned = cleaned.replace(sep, "")  # thousands separators
        elif sep == ",":
            cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class ShopeeScraper:
    """High performance anti-detection scraper for Shopee listings and products."""

    def __init__(
        self,
        session_name: Optional[str] = None,
        headless: bool = True,
        cdp: Optional[Union[str, int]] = None,
    ):
        self.session_name = session_name or settings.default_session_name
        self.headless = headless
        self.cdp = cdp

    def _resolve_cdp(self) -> Optional[Union[str, int]]:
        if self.cdp is not None:
            return None if str(self.cdp).lower() == "none" else self.cdp
        if is_cdp_port_active(9222):
            return 9222
        return None

    async def search(
        self,
        keyword: str,
        limit: int = 50,
        sort_by: str = "relevancy",
        page_number: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Searches products by keyword. Combines network response interception for accuracy
        with progressive human scrolling to trigger dynamic loading.
        """
        intercepted_items: List[Dict[str, Any]] = []

        mgr = BrowserManager(
            headless=self.headless,
            session_name=self.session_name,
            cdp=self._resolve_cdp(),
        )
        page: Optional[Page] = None
        handle_response = None

        try:
            page = await mgr.start()

            # Set up API response listener
            async def _on_response(response: Response):
                url = response.url
                if ("search_items" in url or "/api/v4/search" in url) and response.status == 200:
                    try:
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            data = await response.json()
                            parsed = parse_shopee_api_items(data, settings.base_url)
                            if parsed:
                                intercepted_items.extend(parsed)
                    except Exception as err:
                        logger.debug(f"Could not parse intercepted response: {err}")

            handle_response = _on_response
            page.on("response", handle_response)

            # Build search URL
            encoded_kw = urllib.parse.quote(keyword)
            search_url = f"{settings.base_url}/search?keyword={encoded_kw}"
            if page_number > 0:
                search_url += f"&page={page_number}"

            logger.info(f"Navigating to search page: [cyan]{search_url}[/cyan]")
            await page.goto(search_url, referer=f"{settings.base_url}/", wait_until="domcontentloaded")
            await sleep_random(2.0, 3.5)

            # Human-like scrolling to trigger lazy loading of item cards
            logger.info("Scrolling page to trigger dynamic item loading...")
            await human_scroll(page, steps=6, min_scroll_delta=300, max_scroll_delta=600)
            await sleep_random(1.5, 2.5)

            # Deduplicate intercepted items by item_id
            seen_ids = set()
            unique_items = []
            for it in intercepted_items:
                iid = it.get("item_id")
                if iid and iid not in seen_ids:
                    seen_ids.add(iid)
                    unique_items.append(it)

            logger.info(f"Intercepted {len(unique_items)} items via API.")

            # Fallback to DOM parsing if interception was blocked or empty
            if not unique_items:
                logger.info("API interception returned 0 items; falling back to DOM extraction...")
                dom_items = await self._extract_items_from_dom(page)
                unique_items.extend(dom_items)

            # Trim to requested limit
            final_items = unique_items[:limit]
            logger.info(f"[green]Successfully retrieved {len(final_items)} products for '{keyword}'.[/green]")
            return final_items

        except Exception as e:
            logger.error(f"Error scraping search results: {e}")
            return []
        finally:
            if page and handle_response:
                try:
                    page.remove_listener("response", handle_response)
                except Exception:
                    pass
            await mgr.close()

    async def _extract_items_from_dom(self, page: Page) -> List[Dict[str, Any]]:
        """Fallback DOM-based product card extractor."""
        items: List[Dict[str, Any]] = []
        try:
            cards = await self._first_match_all(
                page,
                [
                    "div.shopee-search-item-result__item",
                    "div[data-sq='item']",
                    "li.shopee-search-item-result__item",
                ],
            )

            for card in cards:
                try:
                    if not (await card.inner_text()).strip():
                        continue

                    link_el = await card.query_selector("a[href]")
                    href = await link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = f"{settings.base_url}{href}"

                    title = await self._first_text(
                        card,
                        [
                            "div[data-sq='item-name']",
                            "div.line-clamp-2",
                            "div[class*='name']",
                            "div[class*='title']",
                        ],
                    )
                    price_str = await self._first_text(
                        card,
                        ["span[class*='price']", "div[class*='price']", "span:has-text('₫')"],
                    )
                    sold_text = await self._first_text(
                        card, ["div:has-text('Đã bán'), div:has-text('Sold')", "span:has-text('Đã bán')"]
                    )

                    if title:
                        items.append({
                            "name": title,
                            "price": parse_price_string(price_str),
                            "price_display": price_str,
                            "historical_sold": self._parse_sold_text(sold_text),
                            "product_url": href,
                        })
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"DOM extraction error: {e}")

        return items

    @staticmethod
    async def _first_match_all(root, selectors: List[str]) -> list:
        """Returns the first selector's matches that yields anything."""
        for sel in selectors:
            found = await root.query_selector_all(sel)
            if found:
                return found
        return []

    @staticmethod
    async def _first_text(root, selectors: List[str]) -> str:
        """Returns the trimmed inner text of the first matching selector, else ''."""
        for sel in selectors:
            el = await root.query_selector(sel)
            if el:
                return (await el.inner_text()).strip()
        return ""

    @staticmethod
    def _parse_sold_text(text: str) -> int:
        """
        Parses 'Đã bán 1,2k' / 'Đã bán 1.234' / 'Đã bán 500' to an integer.

        A bare dot/comma in Vietnamese is a thousands separator, so '1.234' is
        1234 (not 1). Only a trailing 'k'/'tr' multiplies the value.
        """
        if not text:
            return 0
        match = re.search(r"(\d+(?:[.,]\d+)*)\s*(k|tr|triệu)?", text, re.IGNORECASE)
        if not match:
            return 0
        digits = match.group(1)
        suffix = (match.group(2) or "").lower()

        if suffix:  # decimal form such as 1,2k
            num_str = digits.replace(",", ".")
        else:  # thousands separators such as 1.234 or 12,345
            num_str = digits.replace(".", "").replace(",", "")

        try:
            val = float(num_str)
        except ValueError:
            return 0
        if suffix == "k":
            val *= 1_000
        elif suffix:
            val *= 1_000_000
        return int(val)

    async def get_product_detail(self, product_url: str) -> Dict[str, Any]:
        """Scrapes full details from a single product page."""
        mgr = BrowserManager(
            headless=self.headless,
            session_name=self.session_name,
            cdp=self._resolve_cdp(),
        )

        detail: Dict[str, Any] = {"url": product_url}

        try:
            page = await mgr.start()
            logger.info(f"Visiting product detail page: [cyan]{product_url}[/cyan]")
            await page.goto(product_url, referer=f"{settings.base_url}/", wait_until="domcontentloaded")
            await sleep_random(2.0, 3.5)

            # Title
            title_el = await page.query_selector("h1, div.product-briefing span")
            if title_el:
                detail["name"] = (await title_el.inner_text()).strip()

            # Price
            price_el = await page.query_selector("div.product-price, div.pmxafq, div[class*='price']")
            if price_el:
                price_text = (await price_el.inner_text()).strip()
                detail["price_display"] = price_text
                detail["price"] = parse_price_string(price_text)

            # Rating
            rating_el = await page.query_selector("div.product-rating-overview__score, div[class*='rating-score']")
            if rating_el:
                try:
                    detail["rating"] = float((await rating_el.inner_text()).strip())
                except ValueError:
                    detail["rating"] = None

            # Shop name
            shop_el = await page.query_selector("div.section-seller-overview-horizontal__seller-info-wrapper, a[class*='shop-name']")
            if shop_el:
                detail["shop_name"] = (await shop_el.inner_text()).strip()

            # Description
            desc_el = await page.query_selector("div.product-detail__description, div[class*='description']")
            if desc_el:
                detail["description"] = (await desc_el.inner_text()).strip()[:500]

            logger.info(f"[green]Successfully scraped product: {detail.get('name', 'N/A')}[/green]")
            return detail

        except Exception as e:
            logger.error(f"Failed to scrape product detail: {e}")
            return detail
        finally:
            await mgr.close()
