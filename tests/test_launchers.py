"""
Guards the Windows .bat launchers: cmd.exe silently mis-parses them otherwise.

Regression origin: every launcher had LF-only line endings plus an unescaped `&`
in `title`, so double-clicking Chay_Tool_Android.bat printed
    '|| was unexpected at this time.'
and exited before the menu.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHERS = sorted(p for p in ROOT.glob("*.bat") if p.is_file())


def test_launchers_exist():
    assert LAUNCHERS, "no .bat launchers found"


def test_launchers_use_crlf():
    """cmd.exe needs CRLF; LF-only makes `call ... || (...)` and labels break."""
    for path in LAUNCHERS:
        data = path.read_bytes()
        lf_total = data.count(b"\n")
        crlf_total = data.count(b"\r\n")
        assert lf_total == crlf_total, (
            f"{path.name}: {lf_total - crlf_total} bare LF line ending(s); convert the file to CRLF"
        )


def _strip_escapes_and_quotes(line: str) -> str:
    line = re.sub(r"\^.", "", line)          # drop escaped character pairs
    line = re.sub(r'"[^"]*"', '""', line)    # drop quoted spans
    return line


def test_no_unescaped_special_chars_in_echo_and_title():
    for path in LAUNCHERS:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not re.match(r"(?:echo|title)\b", stripped, re.IGNORECASE):
                continue
            bare = _strip_escapes_and_quotes(stripped)
            assert not re.search(r"[&|<>]", bare), (
                f"{path.name}:{lineno}: unescaped cmd operator in echo/title -> {stripped}"
            )


def test_parentheses_escaped_in_echo_inside_blocks():
    """
    An unescaped ')' inside an if/for block closes the block early, and an
    unescaped '(' inside a block breaks parsing. Only echo lines at block
    depth > 0 are checked, because depth 0 echo lines are never ambiguous.
    """
    for path in LAUNCHERS:
        depth = 0
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if depth > 0 and re.match(r"echo\b", stripped, re.IGNORECASE):
                bare = _strip_escapes_and_quotes(stripped)
                assert not re.search(r"[()]", bare), (
                    f"{path.name}:{lineno}: unescaped parenthesis in echo inside a block -> {stripped}"
                )
            unescaped = _strip_escapes_and_quotes(stripped)
            depth += unescaped.count("(") - unescaped.count(")")
            depth = max(depth, 0)


def test_launchers_are_utf8_for_vietnamese_output():
    for path in LAUNCHERS:
        text = path.read_bytes().decode("utf-8")   # raises if not UTF-8
        assert "chcp 65001" in text or text.isascii(), (
            f"{path.name}: non-ASCII text without 'chcp 65001' will render as mojibake"
        )
