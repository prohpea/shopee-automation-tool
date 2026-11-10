
() => {
    // Safety check: Abort immediately if on checkout or cart page
    const curHref = (window.location.href || "").toLowerCase();
    if (curHref.includes("/cart") || curHref.includes("/checkout") || curHref.includes("/buyer/order")) {
        return { claimed_count: 0, vouchers: [] };
    }

    // Keywords indicating voucher claim action
    const claimKeywords = [
        "lưu", "lưu mã", "lưu tất cả", "nhận", "nhận ngay", "nhận mã", "nhận tất cả",
        "thu thập", "thu thập tất cả", "thu thập ngay", "lấy mã", "lấy ngay",
        "nhận voucher", "lưu voucher", "đổi mã", "claim", "collect", "save"
    ];

    // Keywords indicating non-claimable or non-voucher buttons (e.g., terms, cart buttons)
    const excludeKeywords = [
        "đã lưu", "đã nhận", "dùng ngay", "sử dụng", "hết lượt", "đã hết",
        "hết hạn", "sắp diễn ra", "chưa bắt đầu", "chưa diễn ra", "xem thêm",
        "chi tiết", "điều kiện", "lưu ý", "lưu vào", "xem mã", "tìm kiếm",
        "claimed", "used", "expired", "fully redeemed", "redeemed", "t&c",
        "see all", "use", "use now",
        // Safety: ABSOLUTELY FORBID checkout, buy, order, cart, payment actions
        "mua ngay", "mua hàng", "đặt hàng", "đặt đơn", "thanh toán", "thêm vào giỏ",
        "mua với voucher", "chọn mua", "checkout", "place order", "buy now", "buy",
        "order", "thanh toán ngay", "tiến hành thanh toán", "mua ngay với"
    ];

    // High-value ("Voucher Khủng") indicators for priority sniping
    const vipKeywords = [
        "lưu tất cả", "claim all", "nhận tất cả", "thu thập tất cả",
        "100%", "50%", "30%", "25%", "20%",
        "1tr", "2tr", "3tr", "triệu", "1.000k", "500k", "400k", "300k", "250k", "200k", "150k", "100k",
        "0đ", "xtra", "toàn sàn", "freeship", "miễn phí vận chuyển"
    ];

    // Helper to collect elements including within open shadow roots
    function collectCandidateElements(root) {
        const selector = "button, [role='button'], [class*='btn'], [class*='button'], [class*='claim'], [class*='collect'], a, div[class*='shopee-button'], div, span";
        let found = [];
        try {
            found = Array.from(root.querySelectorAll(selector));
        } catch (e) {}

        // Traverse shadow roots
        try {
            const allNodes = root.querySelectorAll('*');
            for (let i = 0; i < allNodes.length; i++) {
                if (allNodes[i].shadowRoot) {
                    found = found.concat(collectCandidateElements(allNodes[i].shadowRoot));
                }
            }
        } catch (e) {}

        return found;
    }

    // Traverse main document and any accessible iframes
    const candidateRoots = [document];
    try {
        const iframes = document.querySelectorAll('iframe');
        for (let i = 0; i < iframes.length; i++) {
            try {
                if (iframes[i].contentDocument) {
                    candidateRoots.push(iframes[i].contentDocument);
                }
            } catch (e) {}
        }
    } catch (e) {}

    let elements = [];
    for (const r of candidateRoots) {
        elements = elements.concat(collectCandidateElements(r));
    }

    const candidates = [];
    const clickedSet = window._shopeeClickedVouchers || (window._shopeeClickedVouchers = new WeakSet());

    for (const el of elements) {
        const clickTarget = el.closest("button, [role='button'], a, div[class*='shopee-button'], div[class*='btn'], div[class*='button']") || el;
        if (clickedSet.has(el) || clickedSet.has(clickTarget)) continue;

        // Skip non-leaf elements unless it's an explicit button
        if (el.children.length > 0 && el.tagName !== "BUTTON" && el.getAttribute("role") !== "button") continue;

        // Skip disabled or hidden elements
        if (el.disabled || el.getAttribute("aria-disabled") === "true") continue;
        const style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        // Normalize text: collapse &nbsp; and multiple whitespace/newlines
        const rawText = el.innerText || el.textContent || "";
        const cleanText = rawText.replace(/[\u00A0\s]+/g, " ").trim().toLowerCase();
        if (!cleanText || cleanText.length > 30) continue;

        // Skip non-claimable states (explicit exclusion)
        if (excludeKeywords.some(ex => cleanText.includes(ex))) continue;

        // Check first line/segment in case of secondary badges
        const firstSegment = cleanText.split(/[\n\r]+/)[0].trim();

        // Check matching claim phrases
        const isClaim = claimKeywords.some(kw =>
            cleanText === kw ||
            cleanText === kw + " mã" ||
            cleanText === "mã " + kw ||
            cleanText === kw + " ngay" ||
            cleanText.startsWith(kw + " ") ||
            firstSegment === kw ||
            firstSegment.startsWith(kw + " ")
        );

        if (isClaim) {
            // Find parent voucher card to extract voucher description/discount
            let card = el.closest("[class*='voucher'], [class*='card'], [class*='coupon'], [class*='ticket'], div[tabindex]");
            if (!card) {
                let curr = el.parentElement;
                for (let depth = 0; depth < 6 && curr; depth++) {
                    const txt = (curr.innerText || "").replace(/[\u00A0\s]+/g, " ").trim();
                    if (txt.length > 15 && txt.length < 300) {
                        card = curr;
                        break;
                    }
                    curr = curr.parentElement;
                }
            }

            let voucherInfo = rawText.replace(/[\u00A0\s]+/g, " ").trim();
            if (card) {
                const textNodes = Array.from(card.querySelectorAll("div, span, p"))
                    .map(n => (n.innerText || "").replace(/[\u00A0\s]+/g, " ").trim())
                    .filter(t => t.length > 2 && t.length < 80 && !claimKeywords.includes(t.toLowerCase()))
                    .slice(0, 3);
                if (textNodes.length > 0) {
                    voucherInfo = textNodes.join(" | ");
                }
            }

            const combinedLower = (cleanText + " " + voucherInfo).toLowerCase();
            let priority = 100;
            let isVip = false;
            if (cleanText.includes("all") || cleanText.includes("tất cả")) {
                priority = 1000;
                isVip = true;
            } else if (vipKeywords.some(vk => combinedLower.includes(vk))) {
                priority = 500;
                isVip = true;
            }

            candidates.push({
                el,
                clickTarget,
                rawText: rawText.replace(/[\u00A0\s]+/g, " ").trim(),
                voucherInfo: voucherInfo.substring(0, 100),
                priority,
                isVip
            });
        }
    }

    // Sort candidates so "Claim All" and "Voucher Khủng" are clicked FIRST at millisecond T=0
    candidates.sort((a, b) => b.priority - a.priority);

    const claimedList = [];
    for (const item of candidates) {
        const { el, clickTarget, rawText, voucherInfo, isVip } = item;
        if (clickedSet.has(el) || clickedSet.has(clickTarget)) continue;
        try {
            const opts = { bubbles: true, cancelable: true, view: window };
            if (typeof window.PointerEvent !== "undefined") {
                clickTarget.dispatchEvent(new PointerEvent('pointerdown', opts));
                clickTarget.dispatchEvent(new PointerEvent('pointerup', opts));
            }
            clickTarget.dispatchEvent(new MouseEvent('mousedown', opts));
            clickTarget.dispatchEvent(new MouseEvent('mouseup', opts));
            clickTarget.click();
            if (clickTarget !== el) {
                el.click();
            }

            clickedSet.add(el);
            if (clickTarget !== el) clickedSet.add(clickTarget);
            claimedList.push({
                button_text: rawText,
                info: voucherInfo,
                is_vip: isVip,
                timestamp: new Date().toISOString()
            });
        } catch (err) {
            // Ignore individual click error
        }
    }

    return {
        claimed_count: claimedList.length,
        vouchers: claimedList
    };
}
