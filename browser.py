import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from config import AD_BLOCK_PATTERNS

try:
    import undetected_chromedriver as uc  # type: ignore
    HAS_UC = True
except Exception:
    HAS_UC = False


def create_stealth_driver(headless=False):
    if HAS_UC:
        opts = uc.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1366,768")
        driver = uc.Chrome(options=opts)
    else:
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--window-size=1366,768")
        driver = webdriver.Chrome(options=opts)
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception:
        pass
    return driver


def set_adblock(driver, enabled: bool):
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": AD_BLOCK_PATTERNS if enabled else []})
    except Exception:
        pass


def close_new_tabs_and_return(driver, base_handle: str):
    try:
        handles = driver.window_handles
        for h in list(handles):
            if h != base_handle:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(base_handle)
    except Exception:
        pass


def guarded_click(driver, element, max_retries: int = 3):
    base = driver.current_window_handle
    for _ in range(max_retries):
        pre_handles = set(driver.window_handles)
        try:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
            except Exception:
                pass
            try:
                ActionChains(driver).move_to_element(element).pause(0.1).click().perform()
            except Exception:
                element.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass
        time.sleep(0.6 + random.uniform(0.1, 0.4))
        post_handles = set(driver.window_handles)
        if len(post_handles) > len(pre_handles):
            close_new_tabs_and_return(driver, base)
            time.sleep(0.4)
            continue
        return True
    return False


