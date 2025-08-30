BASE_ORIGIN = "https://animepahe.ru"
API_BASE = f"{BASE_ORIGIN}/api"

# Network-level adblock URL patterns toggled via Chrome DevTools Protocol
AD_BLOCK_PATTERNS = [
    "*://*.doubleclick.net/*",
    "*://*.googlesyndication.com/*",
    "*://*.google-analytics.com/*",
    "*://*.adservice.google.com/*",
    "*://*.adnxs.com/*",
    "*://*.taboola.com/*",
    "*://*.popads.net/*",
    "*://*.exdynsrv.com/*",
    "*://*.zedo.com/*",
    "*://*.revcontent.com/*",
    "*://*.outbrain.com/*",
    "*://*.advertising.com/*",
    "*://loveplumbertailor.com/*",
]

# Browser configuration
BROWSER_MAX_RETRIES = 3
BROWSER_CREATION_DELAY = 0.5
BROWSER_CLEANUP_DELAY = 0.5
BROWSER_RETRY_DELAY = 2


