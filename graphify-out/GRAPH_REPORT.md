# Graph Report - Shopee_Automation_Tool_v2.0  (2026-11-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 536 nodes · 1169 edges · 26 communities (14 shown, 12 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 133 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- modules/fast_voucher_hunter.py
- cli.py
- ADBDeviceManager
- .execute
- FlashSaleOrderHunter
- AndroidVoucherHunter
- exporter.py
- FastVoucherHunter
- .connect
- adb_device.py
- Settings
- .verify_session
- BrowserManager
- .sniper_hunt
- .auto_247_hunt
- test_scraper_parser.py
- .search
- ShopeeScraper
- .hunt_vouchers
- .start
- test_sniper_auto_refresh_handles_reload_error
- collectCandidateElements
- shopee-automation-tool

## God Nodes (most connected - your core abstractions)
1. `FastVoucherHunter` - 70 edges
2. `ADBDeviceManager` - 33 edges
3. `BrowserManager` - 25 edges
4. `AndroidVoucherHunter` - 22 edges
5. `FlashSaleOrderHunter` - 20 edges
6. `DailyCheckin` - 19 edges
7. `SessionManager` - 18 edges
8. `ShopeeScraper` - 17 edges
9. `AuthManager` - 17 edges
10. `CaptchaDetector` - 17 edges

## Surprising Connections (you probably didn't know these)
- `test_golden_hours_major_has_all_11_slots()` --uses--> `FastVoucherHunter`  [INFERRED]
  tests/test_fast_voucher_hunter.py → shopee_tool/modules/fast_voucher_hunter.py
- `test_restore_session_cookies_if_needed()` --uses--> `Settings`  [INFERRED]
  tests/test_fast_voucher_hunter.py → shopee_tool/core/config.py
- `cmd_detail()` --uses--> `ShopeeScraper`  [INFERRED]
  cli.py → shopee_tool/modules/scraper.py
- `cmd_search()` --uses--> `ShopeeScraper`  [INFERRED]
  cli.py → shopee_tool/modules/scraper.py
- `cmd_login()` --uses--> `AuthManager`  [INFERRED]
  cli.py → shopee_tool/modules/auth.py

## Import Cycles
- None detected.

## Communities (26 total, 12 thin omitted)

### Community 0 - "modules/fast_voucher_hunter.py"
Cohesion: 0.07
Nodes (6): _env_flag(), human_scroll(), sleep_random(), apply_stealth(), test_sleep_random_bounds(), test_sleep_random_defaults_follow_settings()

### Community 1 - "cli.py"
Cohesion: 0.05
Nodes (22): cli(), cmd_auto(), cmd_checkin(), cmd_detail(), cmd_login(), cmd_order(), cmd_verify(), _report() (+14 more)

### Community 2 - "ADBDeviceManager"
Cohesion: 0.08
Nodes (11): ADBDeviceManager, test_batch_rapid_tap_executes_single_shell_loop(), test_batch_rapid_tap_fallback_to_rapid_tap_on_error(), test_connect_device(), test_find_devices_probes_common_ports_if_empty(), test_find_devices_when_already_connected(), test_find_text_bounds_filters_forbidden_keywords(), test_find_text_bounds_from_xml() (+3 more)

### Community 3 - ".execute"
Cohesion: 0.08
Nodes (12): AuthManager, DailyCheckin, CaptchaDetector, test_captcha_detector_attributes(), test_is_captcha_present_negative(), test_is_captcha_present_positive(), test_checkin_already_claimed(), _run() (+4 more)

### Community 4 - "FlashSaleOrderHunter"
Cohesion: 0.08
Nodes (9): FlashSaleOrderHunter, _hunter(), _run(), test_countdown_hh_mm_and_hh_mm_ss_agree(), test_countdown_now_is_immediate(), test_countdown_rejects_extra_segments(), test_dry_run_does_not_click_place_order(), test_total_above_max_price_blocks_order() (+1 more)

### Community 5 - "AndroidVoucherHunter"
Cohesion: 0.10
Nodes (11): cmd_android(), AndroidVoucherHunter, test_auto_247_hunt_with_lead_time(), test_auto_247_single_cycle(), test_calculate_next_golden_hour(), test_connect_brings_shopee_to_foreground(), test_golden_hours_cover_both_hunters(), test_scan_and_claim_taps_new_voucher_after_each_scroll() (+3 more)

### Community 6 - "exporter.py"
Cohesion: 0.15
Nodes (9): export_data(), export_to_csv(), export_to_json(), _resolve_path(), setup_logger(), test_export_data_dispatch(), test_export_empty_data(), test_export_to_csv() (+1 more)

### Community 7 - "FastVoucherHunter"
Cohesion: 0.12
Nodes (18): FastVoucherHunter, test_auto_247_hunt_single_cycle(), _run(), test_check_and_handle_verification(), _run(), test_claim_visible_vouchers_mocked(), _run(), test_close_lifecycle() (+10 more)

### Community 8 - ".connect"
Cohesion: 0.14
Nodes (4): _cdp_http(), _cdp_list_page_tabs(), find_chrome_executable(), is_cdp_port_active()

### Community 9 - "adb_device.py"
Cohesion: 0.13
Nodes (5): _ensure_adb_binary(), _strip_escapes_and_quotes(), test_launchers_use_crlf(), test_no_unescaped_special_chars_in_echo_and_title(), test_parentheses_escaped_in_echo_inside_blocks()

### Community 10 - "Settings"
Cohesion: 0.17
Nodes (5): Settings, ShopeeRegionalConfig, test_default_config(), test_regional_domains(), test_session_paths()

### Community 12 - "BrowserManager"
Cohesion: 0.17
Nodes (3): BrowserManager, SessionManager, test_session_manager_persistence()

### Community 15 - "test_scraper_parser.py"
Cohesion: 0.20
Nodes (8): parse_price_string(), parse_shopee_api_items(), test_all_hubs_keeps_custom_url(), test_parse_api_items_price_below_one_currency_unit(), test_parse_api_items_tier_variations_is_list(), test_parse_empty_shopee_api(), test_parse_price_string(), test_parse_shopee_api_items_scaling()

### Community 16 - ".search"
Cohesion: 0.18
Nodes (3): cmd_search(), _scale_price(), _on_response()

## Knowledge Gaps
- **1 isolated node(s):** `shopee-automation-tool`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 226 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FastVoucherHunter` connect `FastVoucherHunter` to `modules/fast_voucher_hunter.py`, `cli.py`, `.execute`, `AndroidVoucherHunter`, `.connect`, `.verify_session`, `.sniper_hunt`, `.auto_247_hunt`, `test_scraper_parser.py`, `.hunt_vouchers`, `test_sniper_auto_refresh_handles_reload_error`?**
  _High betweenness centrality (0.281) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `FastVoucherHunter` (e.g. with `cmd_auto()` and `cmd_vouchers()`) actually correct?**
  _`FastVoucherHunter` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `shopee-automation-tool` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `modules/fast_voucher_hunter.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07457627118644068 - nodes in this community are weakly interconnected._
- **Why does `ADBDeviceManager` connect `ADBDeviceManager` to `adb_device.py`, `AndroidVoucherHunter`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ADBDeviceManager` (e.g. with `AndroidVoucherHunter` and `test_connect_device()`) actually correct?**
  _`ADBDeviceManager` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `cli.py` be split into smaller, more focused modules?**
  _Cohesion score 0.052600818234950324 - nodes in this community are weakly interconnected._