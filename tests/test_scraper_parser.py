"""
Unit tests for scraper item parsers and price formatters.
"""

from shopee_tool.modules.scraper import parse_shopee_api_items, parse_price_string


def test_parse_price_string():
    assert parse_price_string("₫150.000") == 150000.0
    assert parse_price_string("250.000 đ") == 250000.0
    assert parse_price_string("1.250.000 Đ") == 1250000.0
    assert parse_price_string("$19.99") == 19.99
    assert parse_price_string("invalid") == 0.0
    assert parse_price_string("") == 0.0


def test_parse_shopee_api_items_scaling():
    mock_api_data = {
        "items": [
            {
                "item_basic": {
                    "itemid": 987654321,
                    "shopid": 123456,
                    "name": "Chuột Không Dây Silent",
                    "price": 18900000000,  # Scaled by 100000 => 189,000 VND
                    "price_min": 15000000000,
                    "price_max": 20000000000,
                    "historical_sold": 1520,
                    "item_rating": {"rating_star": 4.876},
                    "discount": "25%",
                    "shop_location": "TP. Hồ Chí Minh",
                    "image": "vn-11134207-7r98o-xyz",
                }
            }
        ]
    }

    parsed = parse_shopee_api_items(mock_api_data, base_url="https://shopee.vn")
    assert len(parsed) == 1
    item = parsed[0]

    assert item["item_id"] == 987654321
    assert item["shop_id"] == 123456
    assert item["name"] == "Chuột Không Dây Silent"
    assert item["price"] == 189000.0
    assert item["min_price"] == 150000.0
    assert item["max_price"] == 200000.0
    assert item["historical_sold"] == 1520
    assert item["rating_star"] == 4.9
    assert item["discount"] == "25%"
    assert "https://shopee.vn/" in item["product_url"]
    assert "vn-11134207-7r98o-xyz" in item["image_url"]


def test_parse_empty_shopee_api():
    parsed = parse_shopee_api_items({})
    assert parsed == []


def test_parse_api_items_tier_variations_is_list():
    """Shopee sends tier_variations as a LIST; it must not be used as a dict."""
    api = {"items": [{
        "itemid": 1,
        "shopid": 2,
        "name": "Áo thun",
        "price": 15000000000,
        "tier_variations": [{"name": "Màu sắc", "options": ["Đỏ"]}],
    }]}
    parsed = parse_shopee_api_items(api)
    assert len(parsed) == 1
    assert parsed[0]["price"] == 150000.0
    assert parsed[0]["shop_location"] == ""


def test_parse_api_items_price_below_one_currency_unit():
    """A 0.80 listing (raw 80000) must stay 0.8, not 80000."""
    api = {"items": [{"itemid": 1, "shopid": 2, "name": "cheap", "price": 80000}]}
    assert parse_shopee_api_items(api)[0]["price"] == 0.8


def test_parse_sold_text_handles_thousands_separators():
    from shopee_tool.modules.scraper import ShopeeScraper

    assert ShopeeScraper._parse_sold_text("Đã bán 1,2k") == 1200
    assert ShopeeScraper._parse_sold_text("Đã bán 1.234") == 1234
    assert ShopeeScraper._parse_sold_text("Đã bán 12.345") == 12345
    assert ShopeeScraper._parse_sold_text("Đã bán 500") == 500
    assert ShopeeScraper._parse_sold_text("") == 0


def test_all_hubs_keeps_custom_url():
    from shopee_tool.modules.fast_voucher_hunter import FastVoucherHunter

    url = "https://shopee.vn/m/mien-phi-van-chuyen"
    hubs = FastVoucherHunter(url=url, all_hubs=True).resolve_hubs()
    assert url in hubs
    assert len(hubs) >= 2

    # Without all_hubs only the requested URL is scanned.
    assert FastVoucherHunter(url=url, all_hubs=False).resolve_hubs() == [url]
