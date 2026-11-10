# 🛍️ Shopee Automation & Scraping Tool

Bộ công cụ tự động hóa trình duyệt và cào dữ liệu Shopee trên Python 3.10+ và Playwright. Thiết kế dạng module, tích hợp kỹ thuật chống phát hiện bot (stealth), lưu phiên đăng nhập và hỗ trợ 7 khu vực Shopee (VN, SG, MY, TH, ID, PH, TW).

---

## 🌟 Tính năng chính

- 🛡️ **Stealth engine**: ghi đè `navigator.webdriver`, mock `window.chrome`, `plugins`, WebGL vendor, `permissions.query`; mô phỏng cuộn trang và độ trễ ngẫu nhiên như người thật.
- 🔑 **Quản lý phiên đăng nhập**: đăng nhập QR/OTP một lần trên trình duyệt thật, lưu `storage_state` (cookies + localStorage) vào `data/sessions/<tên>.json` để tái sử dụng cho các lần chạy ngầm.
- ⚡ **Scraper 2 tầng**: bắt gói tin JSON `/api/v4/search/search_items` từ luồng mạng (chính xác ID, giá, đã bán, đánh giá), tự động fallback sang bóc tách DOM khi API bị chặn. Xuất JSON hoặc CSV (UTF-8 Excel).
- 🎟️ **Săn voucher siêu tốc**: điều khiển Google Chrome thật qua Chrome DevTools Protocol (`--cdp 9222`) để dùng lại phiên đăng nhập sẵn có, đánh giá DOM bằng JavaScript trong mili-giây.
  - Chế độ **fast**: quét nhiều lượt cuộn và bấm toàn bộ nút "Lưu"/"Nhận".
  - Chế độ **sniper**: đếm ngược tới giờ vàng rồi burst liên tục quanh T=0.
  - Chế độ **auto/247**: tự canh mọi khung giờ vàng và giờ cao điểm; giữ **tách kết nối CDP** giữa các mốc để Shopee không nhận diện bot, mỗi lần tải lại trang đều do Chrome tự làm trước khi tool attach.
- 🪙 **Điểm danh Shopee Xu** hằng ngày.
- 🛒 **Săn Flash Sale & đặt đơn 0đ**: chọn biến thể, bấm Mua Ngay, áp voucher, chọn phương thức thanh toán và **chốt chặn giá**: chỉ bấm "Đặt hàng" khi tổng thanh toán đọc được và ≤ ngưỡng cho phép.
- 📱 **Chế độ Android** qua ADB (LDPlayer / MuMu / Nox / điện thoại thật): nhận diện nút voucher bằng màu (Computer Vision) hoặc text, tap hàng loạt trong thiết bị.

---

## 📂 Cấu trúc thư mục

```text
.
├── _bootstrap.bat            # Tạo .venv + cài requirements (dùng chung cho mọi file .bat)
├── main.py                   # Điểm khởi chạy (menu + CLI)
├── cli.py                    # Click CLI
├── fast_voucher_hunter.py    # Script độc lập: chuyển tiếp sang `main.py vouchers`
├── Chay_Tool_Shopee.bat      # Menu tiếng Việt cho Chrome desktop
├── Chay_Tool_Android.bat     # Menu tiếng Việt cho ADB/Android
├── San_Voucher_247.bat       # Chạy auto 24/7
├── claim_vouchers.bat        # Quét nhanh 1 lượt
├── claim_vouchers_sniper.bat # Canh giờ vàng gần nhất
├── San_Sale_0D.bat           # Săn Flash Sale / đặt đơn 0đ
├── start_chrome.bat          # Mở Chrome với cổng CDP 9222
│
├── shopee_tool/
│   ├── core/
│   │   ├── config.py         # Settings từ .env + domain/path theo khu vực
│   │   ├── stealth.py        # Script chống phát hiện bot
│   │   ├── browser.py        # Vòng đời Playwright (thường / persistent / CDP)
│   │   ├── human.py          # Delay, cuộn trang mô phỏng người thật
│   │   ├── session.py        # Đọc/ghi storage_state
│   │   └── adb_device.py     # ADB: tìm thiết bị, tap, vision, hierarchy
│   ├── modules/
│   │   ├── auth.py           # Đăng nhập & kiểm tra phiên
│   │   ├── scraper.py        # Tìm kiếm / chi tiết sản phẩm
│   │   ├── checkin.py        # Điểm danh Xu
│   │   ├── fast_voucher_hunter.py  # Săn voucher (fast/sniper/247)
│   │   ├── android_voucher_hunter.py
│   │   └── flash_sale_order.py     # Săn Flash Sale + chốt chặn giá
│   └── utils/
│       ├── logger.py         # Rich + file log
│       ├── exporter.py       # JSON / CSV
│       └── captcha.py        # Phát hiện captcha / OTP
│
├── data/                     # sessions/, profiles/, exports/
├── logs/                     # shopee.log
└── tests/                    # pytest
```

---

## 🚀 Cài đặt

Cách nhanh nhất: chạy bất kỳ file `.bat` nào — chúng tự gọi `_bootstrap.bat` để tạo `.venv` và cài thư viện trong lần chạy đầu.

Cài thủ công:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

---

## ⚙️ Cấu hình (.env)

Copy `.env.example` thành `.env` rồi chỉnh:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `SHOPEE_REGION` | `vn` | `vn`, `sg`, `my`, `th`, `id`, `ph`, `tw` |
| `HEADLESS` | `false` | `false` để thấy cửa sổ trình duyệt (tiện đăng nhập) |
| `DEFAULT_SESSION` | `default` | Tên file phiên trong `data/sessions/` |
| `MIN_ACTION_DELAY` / `MAX_ACTION_DELAY` | `1.5` / `3.5` | Khoảng nghỉ ngẫu nhiên (giây) |
| `NAV_TIMEOUT_MS` | `45000` | Timeout điều hướng |
| `STEALTH_MODE` | `true` | Bật/tắt script chống phát hiện |
| `USER_AGENT` | *(trống)* | User-Agent tuỳ chỉnh |
| `PROXY_SERVER` / `PROXY_USERNAME` / `PROXY_PASSWORD` | *(trống)* | Proxy dân cư nếu cào số lượng lớn |

---

## 💻 Sử dụng

```powershell
python main.py --help          # Danh sách lệnh
python main.py                 # In hướng dẫn nhanh
```

### Đăng nhập & kiểm tra phiên

```powershell
python main.py login  --session default     # Mở trình duyệt, quét QR / nhập OTP
python main.py verify --session default     # Kiểm tra cookie còn hiệu lực
```

### Tìm kiếm & cào sản phẩm

```powershell
python main.py search --keyword "áo thun" --limit 30 --export csv
python main.py search --keyword "tai nghe bluetooth" --limit 50 --export json --output tai_nghe
python main.py detail --url "https://shopee.vn/product-url-here" --export json
```

Kết quả lưu tại `data/exports/`.

### Điểm danh Shopee Xu

```powershell
python main.py checkin                 # Qua Chrome CDP 9222
python main.py checkin --cdp none      # Qua phiên đã lưu (headless)
```

### Săn voucher

```powershell
python main.py vouchers --mode fast   --cdp 9222   # Quét 1 lượt rồi dừng
python main.py vouchers --mode sniper --cdp 9222 --sniper-time auto
python main.py vouchers --mode auto   --cdp 9222   # 24/7 tự canh giờ vàng
python main.py auto                                # Viết tắt của --mode auto
python fast_voucher_hunter.py --cdp 9222           # Tương đương main.py vouchers --mode auto
```

Tuỳ chọn đáng chú ý:

- `--all-hubs`: quét cả trang voucher sàn và trang mã miễn phí vận chuyển.
- `--patrol-interval 900`: chu kỳ tuần tra nhẹ khi chờ giờ vàng (`0` = tắt).
- `--scrolls 6`: số lượt cuộn mỗi lần quét.
- `--max 200`: số voucher tối đa mỗi lượt.
- `--cdp none`: chạy Chrome persistent profile thay vì kết nối cổng debug.

Nếu cổng 9222 chưa mở, tool tự khởi chạy Chrome Desktop với profile thật của bạn (`mklink /J` tới `%LOCALAPPDATA%\Google\Chrome\User Data`) để giữ nguyên đăng nhập. Chạy `start_chrome.bat` nếu muốn tự mở thủ công.

### Săn Flash Sale / đặt đơn 0đ

```powershell
python main.py order --url "https://shopee.vn/..." --time 00:00:00 --max-price 0 --dry-run
```

Luôn chạy `--dry-run` trước: tool sẽ dừng ở trang Checkout mà không bấm "Đặt hàng".
Nếu **không đọc được** tổng thanh toán, tool coi như thất bại và **không đặt hàng** (không bao giờ mặc định là 0đ).

### Android (ADB)

```powershell
python main.py android --mode auto
python main.py android --mode fast --scrolls 3
python main.py android --mode sniper --x 400 --y 800 --tap-count 50
```

---

## 📱 File `.bat`

| File | Việc nó làm |
| --- | --- |
| `Chay_Tool_Shopee.bat` | Menu: xác minh đăng nhập, săn 24/7, quét nhanh, sniper, đặt đơn 0đ, điểm danh, tìm kiếm, chuyển sang Android |
| `Chay_Tool_Android.bat` | Menu ADB: săn 24/7, quét nhanh, sniper tap, mở app Shopee, kiểm tra kết nối |
| `San_Voucher_247.bat` | Chạy thẳng chế độ auto 24/7 |
| `claim_vouchers.bat` | Quét nhanh 1 lượt |
| `claim_vouchers_sniper.bat` | Canh khung giờ vàng gần nhất |
| `San_Sale_0D.bat` | Nhập link / giờ / giá tối đa / dry-run để săn Flash Sale |
| `start_chrome.bat` | Mở Chrome với `--remote-debugging-port=9222` |

---

## 🛡️ Chống khóa tài khoản

1. **Đừng quét quá dày**: giữ nghỉ 1.5–4 giây giữa các thao tác (`MIN/MAX_ACTION_DELAY`).
2. **Dùng phiên đã đăng nhập**: khách vãng lai bị giới hạn kết quả tìm kiếm.
3. **Xoay proxy** khi cào hàng nghìn sản phẩm/ngày.
4. **Đừng mở nhiều trình duyệt cùng lúc trên một IP**.
5. Chế độ 24/7 cố ý **không attach CDP** trong lúc chờ: debugger gắn vào lúc tải trang là dấu hiệu bot rõ ràng nhất với Shopee.

---

## 🧪 Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

80 test, bao gồm: parser giá/sold, parse API, session, cấu hình khu vực, stealth, captcha, exporter, ADB, chốt chặn giá của Flash Sale, các luồng săn voucher (mock + DOM thật qua Playwright), và bộ chặn tái phát lỗi cú pháp file `.bat`.

> Hai test DOM thật khởi chạy Chromium nên cần thư mục `%TEMP%` ghi được. Nếu môi trường chặn `mkdtemp`, chúng sẽ báo `EPERM` — đặt `TEMP` sang một thư mục ghi được hoặc chạy `playwright install chromium`.

---

## 🧠 Knowledge graph (`/graphify`)

Codebase đã được index thành knowledge graph để hỏi thẳng kiến trúc thay vì grep từng file. Dữ liệu graph ở [graphify-out/](graphify-out/).

Cài CLI (một lần, toàn máy) rồi cài skill cho agent của bạn:

```powershell
uv tool install graphifyy
graphify install --project --platform agents
```

Skill được cài vào `.agents/skills/graphify/` và **không** commit vào repo (nội dung bên thứ ba, tái tạo được bằng lệnh trên).

Hỏi graph:

```powershell
graphify query "luồng chốt chặn giá trước khi đặt hàng chạy thế nào?"
graphify explain "FlashSaleOrderHunter"
graphify path "FastVoucherHunter" "Settings"
```

Cập nhật sau khi sửa code (không cần LLM, không cần API key):

```powershell
graphify update .
```

Mở [graphify-out/graph.html](graphify-out/graph.html) bằng trình duyệt để xem graph tương tác.

> Graph hiện tại: 536 node · 1169 cạnh · 26 community, 89% cạnh `EXTRACTED` (đọc trực tiếp từ AST). Chạy `--code-only` với `GRAPHIFY_BACKEND=none` nên không có dữ liệu nào rời khỏi máy.

---

## 📄 Bản quyền

MIT. Dành cho mục đích học tập, nghiên cứu và tự động hóa tác vụ cá nhân.
