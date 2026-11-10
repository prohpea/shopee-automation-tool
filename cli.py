"""
Shopee Automation Tool - Command Line Interface.
Provides unified commands for login, searching, scraping, daily coins, and vouchers.
"""

import asyncio
import sys
import click

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.table import Table

from shopee_tool.modules.auth import AuthManager
from shopee_tool.modules.scraper import ShopeeScraper
from shopee_tool.modules.checkin import DailyCheckin
from shopee_tool.modules.fast_voucher_hunter import FastVoucherHunter
from shopee_tool.modules.android_voucher_hunter import AndroidVoucherHunter
from shopee_tool.modules.flash_sale_order import FlashSaleOrderHunter
from shopee_tool.utils.exporter import export_data
from shopee_tool.utils.logger import console


def _report(res: dict) -> int:
    """Prints a result message and returns the process exit code."""
    if res.get("success"):
        console.print(f"[bold green]✓ {res['message']}[/bold green]")
        return 0
    console.print(f"[bold red]✗ {res.get('message', 'Thất bại')}[/bold red]")
    return 1


@click.group()
def cli():
    """Shopee Automation & Scraping Tool CLI."""
    pass


@cli.command("login")
@click.option("--session", "-s", default="default", help="Session profile name (e.g. account1)")
@click.option("--timeout", "-t", default=180, help="Timeout in seconds for interactive login")
def cmd_login(session: str, timeout: int):
    """Launch visible browser to log in (QR Code / SMS OTP) and save session."""
    auth = AuthManager(session_name=session)
    if asyncio.run(auth.interactive_login(timeout_seconds=timeout)):
        console.print(f"[bold green]✓ Session '{session}' ready for automation![/bold green]")
    else:
        console.print("[bold red]✗ Login was not completed.[/bold red]")
        sys.exit(1)


@cli.command("verify")
@click.option("--session", "-s", default="default", help="Session profile name")
def cmd_verify(session: str):
    """Verify if saved session cookies are still valid and authenticated."""
    auth = AuthManager(session_name=session)
    if asyncio.run(auth.verify_session()):
        console.print(f"[bold green]✓ Session '{session}' is active.[/bold green]")
    else:
        console.print("[bold red]✗ Session '{session}' is invalid or expired.[/bold red]")
        sys.exit(1)


@cli.command("search")
@click.option("--keyword", "-k", required=True, help="Search keyword (e.g. 'áo thun', 'tai nghe')")
@click.option("--limit", "-l", default=20, help="Maximum number of items to return")
@click.option("--export", "-e", type=click.Choice(["csv", "json"]), default="json", help="Export format")
@click.option("--output", "-o", default=None, help="Output file name without extension")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--session", "-s", default="default", help="Session name to use")
def cmd_search(keyword: str, limit: int, export: str, output: str, headless: bool, session: str):
    """Search products on Shopee and export results to CSV/JSON."""
    scraper = ShopeeScraper(session_name=session, headless=headless)
    items = asyncio.run(scraper.search(keyword=keyword, limit=limit))

    if not items:
        console.print(f"[yellow]No items found for keyword '{keyword}'.[/yellow]")
        return

    table = Table(title=f"Shopee Search Results: '{keyword}' ({len(items)} items)")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Product Name", style="white", max_width=45, overflow="ellipsis")
    table.add_column("Price (VND)", justify="right", style="green")
    table.add_column("Sold", justify="right", style="magenta")
    table.add_column("Rating", justify="right", style="yellow")

    for i, it in enumerate(items[:15], 1):
        price_val = it.get("price", 0)
        table.add_row(
            str(i),
            it.get("name", "")[:50],
            f"{int(price_val):,}" if price_val else "N/A",
            f"{it.get('historical_sold', 0):,}",
            str(it.get("rating_star", "N/A")),
        )

    console.print(table)

    out_name = output or f"search_{keyword.replace(' ', '_')}"
    file_path = export_data(items, fmt=export, filename=out_name)
    console.print(f"[bold green]Saved {len(items)} items to: {file_path}[/bold green]")


@cli.command("detail")
@click.option("--url", "-u", required=True, help="Direct URL of the Shopee product")
@click.option("--export", "-e", type=click.Choice(["csv", "json"]), default="json", help="Export format")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
def cmd_detail(url: str, export: str, headless: bool):
    """Extract detailed information from a product page."""
    scraper = ShopeeScraper(headless=headless)
    detail = asyncio.run(scraper.get_product_detail(url))

    table = Table(title="Shopee Product Details")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    for k, v in detail.items():
        table.add_row(k, str(v))
    console.print(table)

    file_path = export_data([detail], fmt=export, filename="product_detail")
    console.print(f"[bold green]Saved detail to: {file_path}[/bold green]")


@cli.command("checkin")
@click.option("--cdp", "-c", default="9222", help="Chrome CDP port (default: 9222) or 'none'")
@click.option("--session", "-s", default="default", help="Session profile name (if cdp=none)")
@click.option("--headless/--no-headless", default=False, help="Run browser in headless mode")
def cmd_checkin(cdp: str, session: str, headless: bool):
    """Claim daily Shopee coins check-in reward."""
    bot = DailyCheckin(session_name=session, headless=headless, cdp=cdp)
    res = asyncio.run(bot.execute())
    if res["success"]:
        console.print(f"[bold green]✓ {res['message']}[/bold green]")
    else:
        console.print(f"[bold red]✗ {res['message']}[/bold red]")


@cli.command("vouchers")
@click.option(
    "--mode",
    "-M",
    type=click.Choice(["auto", "247", "fast", "sniper"]),
    default="fast",
    help="'auto'/'247' (24/7 Golden Hour Auto-Pilot), 'fast' (multi-scroll DOM claim), 'sniper' (flash drop burst)",
)
@click.option("--cdp", "-c", default="9222", help="Chrome CDP debugging port (e.g. 9222) or 'none' for standalone")
@click.option("--url", "-u", default=None, help="Target voucher hub URL (default: Shopee voucher hub)")
@click.option("--all-hubs", is_flag=True, default=False, help="Scan both Platform Voucher and Free Shipping hubs")
@click.option("--sniper-time", "-t", default=None, help="Sniper target time (HH:MM:SS, 'auto', or omit for continuous refresh)")
@click.option("--refresh-interval", "-r", default=0.5, type=float, help="Auto-refresh interval in seconds for sniper mode")
@click.option("--patrol-interval", "-p", default=900.0, type=float, help="Patrol scan interval in seconds during 24/7 mode (0 = off)")
@click.option("--scrolls", default=6, type=int, help="Number of scroll passes down the voucher hub (fast/auto mode)")
@click.option("--max", "-m", default=200, type=int, help="Maximum number of vouchers to claim per sweep")
@click.option("--headless/--no-headless", default=False, help="Run browser in headless mode")
@click.option("--user-data-dir", default=None, help="Custom Chrome user data directory for the persistent profile")
def cmd_vouchers(
    mode: str,
    cdp: str,
    url: str,
    all_hubs: bool,
    sniper_time: str,
    refresh_interval: float,
    patrol_interval: float,
    scrolls: int,
    max: int,
    headless: bool,
    user_data_dir: str,
):
    """Collect available vouchers and discount codes (supports 24/7 Golden Hour Auto-Pilot)."""
    hunter = FastVoucherHunter(
        cdp=cdp,
        url=url,
        all_hubs=all_hubs,
        headless=headless,
        user_data_dir=user_data_dir,
        max_claims=max,
    )
    try:
        if mode in ("auto", "247"):
            res = asyncio.run(
                hunter.auto_247_hunt(patrol_interval=patrol_interval, scroll_rounds=scrolls)
            )
        elif mode == "sniper":
            res = asyncio.run(
                hunter.sniper_hunt(target_time_str=sniper_time, refresh_interval=refresh_interval)
            )
        else:
            res = asyncio.run(hunter.hunt_vouchers(scroll_rounds=scrolls))
    except ConnectionError:
        sys.exit(1)

    sys.exit(_report(res))


@cli.command("auto")
@click.option("--cdp", "-c", default="9222", help="Chrome CDP debugging port (default: 9222)")
@click.option("--patrol-interval", "-p", default=900.0, type=float, help="Patrol scan interval in seconds (0 = off)")
@click.option("--scrolls", default=6, type=int, help="Number of scroll passes per sweep")
def cmd_auto(cdp: str, patrol_interval: float, scrolls: int):
    """Run 24/7 Non-Stop Golden Hour & Peak Drop Voucher Hunter."""
    hunter = FastVoucherHunter(cdp=cdp, max_claims=500)
    try:
        res = asyncio.run(
            hunter.auto_247_hunt(patrol_interval=patrol_interval, scroll_rounds=scrolls)
        )
    except ConnectionError:
        sys.exit(1)
    sys.exit(_report(res))


@cli.command("android")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["auto", "fast", "sniper"], case_sensitive=False),
    default="auto",
    help="auto (24/7 golden hours), fast (scan & claim now), sniper (rapid tap at coords)",
)
@click.option("--device", "-d", default=None, help="ADB device serial or IP:port (e.g. 127.0.0.1:5555)")
@click.option("--scrolls", "-s", default=3, type=int, help="Number of scroll passes for voucher scanning")
@click.option("--x", default=None, type=int, help="X coordinate for sniper tap")
@click.option("--y", default=None, type=int, help="Y coordinate for sniper tap")
@click.option("--tap-count", default=30, type=int, help="Number of rapid taps for sniper mode")
def cmd_android(mode: str, device: str, scrolls: int, x: int, y: int, tap_count: int):
    """Run Voucher Hunter on Android Emulator via ADB."""
    hunter = AndroidVoucherHunter(device_serial=device)
    try:
        hunter.connect()
    except Exception as e:
        console.print(f"[bold red]✗ Lỗi kết nối giả lập: {e}[/bold red]")
        sys.exit(1)

    if mode == "auto":
        hunter.auto_247_hunt()
    elif mode == "sniper":
        if x is None or y is None:
            console.print("[yellow]Chưa chỉ định toạ độ (--x, --y), tự động quét vị trí nút trên màn hình...[/yellow]")
            hunter.scan_and_claim_vouchers(max_scrolls=1)
        else:
            hunter.sniper_tap(x, y, count=tap_count)
    else:
        count = hunter.scan_and_claim_vouchers(max_scrolls=scrolls)
        console.print(f"[bold green]✓ Hoàn thành quét voucher: Đã lưu {count} voucher![/bold green]")


@cli.command("order")
@click.option("--url", "-u", required=True, help="Shopee product URL to snipe & buy")
@click.option("--time", "-t", default="now", help="Target flash drop time (HH:MM:SS, e.g. '00:00:00' or 'now')")
@click.option("--max-price", "-p", default=0, type=int, help="Maximum allowable total payment in VND (default: 0 for 0đ items)")
@click.option("--variant", "-v", default=None, help="Product variant name to select (e.g. 'Đen', 'Size L')")
@click.option("--payment", default="COD", type=click.Choice(["COD", "ShopeePay"], case_sensitive=False), help="Payment method (default: COD)")
@click.option("--cdp", "-c", default="9222", help="Chrome CDP port (default: 9222)")
@click.option("--dry-run/--no-dry-run", default=False, help="Test run: stop at checkout page without clicking Place Order")
@click.option("--headless/--no-headless", default=False, help="Run in headless browser mode")
def cmd_order(url: str, time: str, max_price: int, variant: str, payment: str, cdp: str, dry_run: bool, headless: bool):
    """Snipe Flash Sale products and auto-place 0đ orders with price safety gate."""
    hunter = FlashSaleOrderHunter(
        item_url=url,
        target_time_str=time,
        variant=variant,
        max_price=max_price,
        payment_method=payment,
        cdp=cdp,
        dry_run=dry_run,
        headless=headless,
    )
    try:
        res = asyncio.run(hunter.execute_hunt())
    except ConnectionError:
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗ Lỗi thực thi săn đơn: {e}[/bold red]")
        sys.exit(1)
    sys.exit(_report(res))


if __name__ == "__main__":
    cli()
