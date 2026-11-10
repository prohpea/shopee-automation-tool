"""
Shopee Automation Tool - Main Entry Point.
Run `python main.py --help` or `python main.py` for interactive launcher.
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from cli import cli


def main():
    if len(sys.argv) > 1:
        cli()
    else:
        # If no arguments provided, show help / interactive menu
        print("\n=== Shopee Automation & Scraping Tool ===")
        print("Usage: python main.py [COMMAND] [OPTIONS]\n")
        print("Available Commands:")
        print("  auto      - Run 24/7 Non-Stop Golden Hour & Peak Drop Voucher Hunter")
        print("  vouchers  - Collect platform and free shipping vouchers (fast / auto / sniper)")
        print("  checkin   - Claim daily Shopee coins")
        print("  login     - Log in interactively (QR code / OTP) & save session")
        print("  verify    - Verify saved session validity")
        print("  search    - Search products and export to CSV/JSON")
        print("  detail    - Scrape product details from URL")
        print("\nRun 'python main.py [COMMAND] --help' for details on each command.\n")
        cli(["--help"])


if __name__ == "__main__":
    main()
