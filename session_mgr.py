import time
import urllib.parse
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import BASE_ORIGIN
from browser import create_stealth_driver


def looks_like_ddos_guard(resp: requests.Response) -> bool:
    try:
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            return False
    except Exception:
        pass
    text_head = (resp.text or "")[:1000].lower()
    return "ddos-guard" in text_head or "js-challenge" in text_head


def wait_for_ddos_clear(driver, timeout=20):
    driver.get(BASE_ORIGIN)
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input#search, .search"))
        )
        return
    except Exception:
        pass
    start = time.time()
    while time.time() - start < timeout:
        html = driver.page_source or ""
        if "DDoS-Guard" not in html:
            return
        for c in driver.get_cookies():
            if c.get("name", "").startswith("__ddg"):
                return
        time.sleep(1.0)


def get_requests_session_from_selenium():
    driver = create_stealth_driver(headless=True)
    print("🌐 Opening Animepahe…")
    wait_for_ddos_clear(driver)
    cookies = driver.get_cookies()
    driver.quit()
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": BASE_ORIGIN + "/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
    })
    for c in cookies:
        sess.cookies.set(c["name"], c["value"], domain=c.get("domain"))
    return sess


class SessionManager:
    def __init__(self):
        self.session = get_requests_session_from_selenium()

    def refresh_cookies(self):
        print("🔄 Refreshing cookies via Selenium…")
        self.session = get_requests_session_from_selenium()

    def get(self, url, **kwargs):
        r = self.session.get(url, **kwargs)
        if looks_like_ddos_guard(r):
            print("🛑 DDoS page detected. Refreshing…")
            self.refresh_cookies()
            r = self.session.get(url, **kwargs)
        elif r.status_code == 403:
            print("🛑 403 Forbidden. Refreshing…")
            self.refresh_cookies()
            r = self.session.get(url, **kwargs)
        return r


