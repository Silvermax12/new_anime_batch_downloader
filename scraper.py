import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from browser import create_stealth_driver, guarded_click


def scrape_download_links(anime_session, episode_session):
    url = f"https://animepahe.ru/play/{anime_session}/{episode_session}"

    driver = create_stealth_driver(headless=False)
    driver.get(url)

    links = {}
    try:
        download_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "downloadMenu"))
        )
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
            download_button.click()
        except Exception:
            guarded_click(driver, download_button, max_retries=3)

        dropdown = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "pickDownload"))
        )

        anchors = dropdown.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            href = a.get_attribute("href")
            text = a.text.strip()
            match = re.search(r"(\d{3,4})p", text)
            if href and match:
                quality = match.group(1)
                if "eng" in text.lower():
                    lang = "eng"
                elif "chi" in text.lower():
                    lang = "chi"
                else:
                    lang = "jpn"
                links[f"{quality}_{lang}"] = href

    except TimeoutException as ex:
        print("⚠️ Could not locate download links (timeout):", ex)
    except Exception as ex:
        print("⚠️ Could not locate download links:", ex)

    driver.quit()
    return links


