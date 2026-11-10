"""
Fast Voucher Hunter - Standalone entry point.

Kept for the documented `python fast_voucher_hunter.py --cdp 9222` invocation.
It simply forwards to `main.py vouchers` in auto (24/7) mode, so there is only
one CLI dialect to maintain.

Usage:
  python fast_voucher_hunter.py --cdp 9222
  python fast_voucher_hunter.py --cdp 9222 --mode sniper --sniper-time 12:00:00
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from cli import cli


def main() -> None:
    argv = [a.replace("--target-time", "--sniper-time") for a in sys.argv[1:]]
    args = ["vouchers"] + argv
    if not any(a in ("--mode", "-M") for a in argv):
        args += ["--mode", "auto"]
    cli.main(args=args, prog_name="fast_voucher_hunter.py")


if __name__ == "__main__":
    main()
