"""
Shopee Automation Tool - Anti-Detection Stealth Module.
Injects comprehensive, idempotent browser fingerprint evasions to bypass bot detection.
"""

from playwright.async_api import BrowserContext

STEALTH_JS = """
(() => {
    try {
        // 1. Hide navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    } catch (e) {}

    try {
        // Remove CDP / automation artifact variables if present
        const cdcProps = Object.getOwnPropertyNames(window).filter(
            p => p.startsWith('cdc_') || p.startsWith('$cdc_') || p.includes('webdriver')
        );
        for (const prop of cdcProps) {
            try { delete window[prop]; } catch (e) {}
        }
    } catch (e) {}

    try {
        // 2. Mock Chrome runtime and csi
        if (!window.chrome) {
            window.chrome = {};
        }
        if (!window.chrome.runtime) {
            window.chrome.runtime = {
                PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' },
                PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64' },
                PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64' },
                connect: function() {},
                sendMessage: function() {}
            };
        }
        if (!window.chrome.csi) {
            window.chrome.csi = function() {
                return {
                    startE: Date.now(),
                    onloadT: Date.now() + 500,
                    pageT: 1200.45,
                    tran: 15
                };
            };
        }
        if (!window.chrome.loadTimes) {
            window.chrome.loadTimes = function() {
                return {
                    requestTime: (Date.now() - 1000) / 1000,
                    startLoadTime: (Date.now() - 950) / 1000,
                    commitLoadTime: (Date.now() - 800) / 1000,
                    finishDocumentLoadTime: (Date.now() - 300) / 1000,
                    finishLoadTime: (Date.now() - 100) / 1000,
                    firstPaintTime: (Date.now() - 600) / 1000,
                    firstPaintAfterLoadTime: 0,
                    navigationType: 'Other',
                    wasFetchedViaSpdy: true,
                    wasNpnNegotiated: true,
                    npnNegotiatedProtocol: 'h2',
                    wasAlternateProtocolAvailable: false,
                    connectionInfo: 'h2'
                };
            };
        }
    } catch (e) {}

    try {
        // 3. Mock navigator.plugins and mimeTypes
        const fakePlugins = [
            {
                name: "Chrome PDF Plugin",
                filename: "internal-pdf-viewer",
                description: "Portable Document Format",
                mimeTypes: [{ type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format" }]
            },
            {
                name: "Chrome PDF Viewer",
                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                description: "",
                mimeTypes: [{ type: "application/pdf", suffixes: "pdf", description: "" }]
            },
            {
                name: "Native Client",
                filename: "internal-nacl-plugin",
                description: "",
                mimeTypes: [{ type: "application/x-nacl", suffixes: "", description: "" }]
            }
        ];

        Object.defineProperty(navigator, 'plugins', {
            get: () => fakePlugins,
            configurable: true
        });
    } catch (e) {}

    try {
        // 4. Fix permissions.query
        if (navigator.permissions && navigator.permissions.query && !navigator.permissions._stealthPatched) {
            const originalQuery = navigator.permissions.query.bind(navigator.permissions);
            navigator.permissions.query = (parameters) => {
                if (parameters && parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission, onchange: null });
                }
                return originalQuery(parameters);
            };
            navigator.permissions._stealthPatched = true;
        }
    } catch (e) {}

    try {
        // 5. Realistic WebGL Vendor & Renderer
        if (typeof WebGLRenderingContext !== 'undefined' && !WebGLRenderingContext.prototype._stealthPatched) {
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Google Inc. (Intel)';
                if (parameter === 37446) return 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter.apply(this, arguments);
            };
            WebGLRenderingContext.prototype._stealthPatched = true;
        }

        if (typeof WebGL2RenderingContext !== 'undefined' && !WebGL2RenderingContext.prototype._stealthPatched) {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Google Inc. (Intel)';
                if (parameter === 37446) return 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)';
                return getParameter2.apply(this, arguments);
            };
            WebGL2RenderingContext.prototype._stealthPatched = true;
        }
    } catch (e) {}

    try {
        // 6. Hairline feature fix
        Object.defineProperty(screen, 'availTop', { get: () => 0, configurable: true });
        Object.defineProperty(screen, 'availLeft', { get: () => 0, configurable: true });
    } catch (e) {}
})();
"""


async def apply_stealth(context: BrowserContext) -> None:
    """Injects stealth scripts to all current and future pages in the browser context."""
    await context.add_init_script(STEALTH_JS)
    for page in getattr(context, "pages", []):
        try:
            if not page.is_closed():
                await page.evaluate(STEALTH_JS)
        except Exception:
            pass
