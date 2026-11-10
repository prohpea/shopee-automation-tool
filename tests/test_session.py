"""
Unit tests for session and cookie manager.
"""

import json
from pathlib import Path
from shopee_tool.core.session import SessionManager


def test_session_manager_persistence(tmp_path: Path):
    session_file = tmp_path / "test_sess.json"
    mgr = SessionManager(session_name="test_sess")
    mgr.session_path = session_file

    assert not mgr.exists()
    assert mgr.read_cookies() == []
    assert mgr.get_shopee_token() is None

    # Write mock storage state
    mock_state = {
        "cookies": [
            {"name": "SPC_EC", "value": "test_token_12345", "domain": ".shopee.vn"},
            {"name": "SPC_U", "value": "999888", "domain": ".shopee.vn"},
        ],
        "origins": [],
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(mock_state, f)

    assert mgr.exists()
    cookies = mgr.read_cookies()
    assert len(cookies) == 2
    assert mgr.get_shopee_token() == "test_token_12345"

    # Delete
    assert mgr.delete_session() is True
    assert not mgr.exists()
