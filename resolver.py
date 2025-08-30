import time
import os
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
from browser import (
    create_stealth_driver,
    set_adblock,
    guarded_click,
    cleanup_browser_data,
)


def _remove_ads_and_overlays(driver):
    ad_selectors = [
        "a[href*='loveplumbertailor.com']",
        "a[href*='doubleclick']",
        "a[href*='googlesyndication']",
        "iframe[src*='ads']",
        ".ad-overlay",
        ".popup-overlay",
        "#lk4w",
    ]
    for selector in ad_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    try:
                        el.click()
                        time.sleep(0.25)
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].remove();", el)
                        except Exception:
                            pass
        except Exception:
            continue


def resolve_download_info(intermediate_url):
    """
    Resolve download information including URL, form data, cookies, and filename.
    Returns a dict with all necessary info for downloading.
    """
    driver = create_stealth_driver(headless=True)
    download_info = {
        'url': None,
        'form_data': {},
        'cookies': {},
        'headers': {},
        'filename': None
    }
    
    try:
        print("🌐 Navigating to intermediate URL...")
        set_adblock(driver, True)
        driver.get(intermediate_url)

        # Continue button handling with improved logic
        try:
            # Close any extra windows/tabs that might have opened
            if len(driver.window_handles) > 1:
                for handle in driver.window_handles[1:]:
                    driver.switch_to.window(handle)
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])

            # Wait for the "Continue" button to load and be visible
            continue_button_locator = (By.CLASS_NAME, "redirect")
            WebDriverWait(driver, 60).until(EC.visibility_of_element_located(continue_button_locator))

            # Wait an additional 6 seconds before attempting to click the "Continue" button
            sleep(6)

            # Retry clicking the continue button a few times if necessary
            for _ in range(3):
                try:
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(continue_button_locator))
                    continue_button = driver.find_element(*continue_button_locator)
                    driver.execute_script("arguments[0].click();", continue_button)
                    print("✅ Continue button clicked successfully")
                    break  # Exit loop if click is successful
                except ElementClickInterceptedException:
                    print("Click was intercepted, trying again...")
                    sleep(2)
        except Exception as e:
            print("⚠️ Continue handling error:", e)

        # Progress by URL/domain heuristics
        deadline = time.time() + 30
        while time.time() < deadline:
            current_url = driver.current_url
            if "/d/" in current_url or current_url.endswith(".mp4"):
                download_info['url'] = current_url
                print("✅ Direct download URL reached:", current_url)
                break
            if "kwik.si" in current_url:
                break
            time.sleep(0.5)

        # Extract episode title for filename
        try:
            title_locator = (By.CLASS_NAME, "title")
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(title_locator))
            title_element = driver.find_element(*title_locator)
            episode_title = title_element.text.strip()
            filename = episode_title.replace(" ", "_")
            download_info['filename'] = filename
            print(f"📝 Episode title extracted: {episode_title}")
        except Exception as e:
            print(f"⚠️ Could not extract episode title: {e}")

        # Extract download URL and form data
        print("🔍 Extracting download information...")
        set_adblock(driver, False)
        time.sleep(1.0)
        
        # Handle potential ad pages or intermediate pages
        download_button_locator = (By.CSS_SELECTOR, "button[type='submit']")
        retries = 3
        
        for attempt in range(retries):
            try:
                download_button = WebDriverWait(driver, 45).until(EC.element_to_be_clickable(download_button_locator))
                form = download_button.find_element(By.XPATH, './ancestor::form')
                download_url = form.get_attribute('action')
                
                if download_url and "http" in download_url:
                    download_info['url'] = download_url
                    print(f"✅ Download URL extracted: {download_url}")
                    break
            except ElementClickInterceptedException as e:
                print(f"Attempt {attempt + 1} failed due to element click interception: {e}")
                sleep(2)

        if not download_info['url']:
            raise Exception("Failed to extract the download URL after retries.")

        # Extract cookies from the Selenium session
        cookies = driver.get_cookies()
        for cookie in cookies:
            download_info['cookies'][cookie['name']] = cookie['value']

        # Collect any necessary hidden form data
        form_inputs = driver.find_elements(By.XPATH, '//form//input')
        for input_element in form_inputs:
            name = input_element.get_attribute('name')
            value = input_element.get_attribute('value')
            if name:
                download_info['form_data'][name] = value

        # Add headers to simulate a real browser request
        download_info['headers'] = {
            'User-Agent': driver.execute_script("return navigator.userAgent;"),
            'Referer': driver.current_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        print("✅ Download information successfully extracted")
        return download_info

    except Exception as e:
        print(f"⚠️ Error resolving download info: {e}")
        return None
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        try:
            cleanup_browser_data(driver)
        except Exception:
            pass


def resolve_download_url(intermediate_url):
    """
    Legacy function for backwards compatibility.
    Returns just the URL for existing code that expects it.
    """
    download_info = resolve_download_info(intermediate_url)
    return download_info['url'] if download_info else None


