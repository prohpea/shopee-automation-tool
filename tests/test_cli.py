"""
Unit tests for CLI command definitions.
"""

from click.testing import CliRunner
from cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Shopee Automation & Scraping Tool CLI" in result.output
    assert "login" in result.output
    assert "search" in result.output
    assert "checkin" in result.output
    assert "vouchers" in result.output


def test_search_command_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--help"])
    assert result.exit_code == 0
    assert "--keyword" in result.output
    assert "--limit" in result.output
    assert "--export" in result.output


def test_checkin_command_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["checkin", "--help"])
    assert result.exit_code == 0
    assert "--cdp" in result.output
    assert "--session" in result.output


def test_android_command_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["android", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "--device" in result.output

