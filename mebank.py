"""Script to download transactions CSV from ME Bank."""

import argparse
import glob
import os
from pathlib import Path
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


def find(driver: webdriver, by: By, value: str, time: int = 10) -> WebElement:
    """Wait and scroll to clickable Selenium element."""
    obj = WebDriverWait(driver, time).until(EC.element_to_be_clickable((by, value)))
    driver.execute_script("arguments[0].scrollIntoView();", obj)
    return obj


def newest_file(path: str) -> str:
    """Return newest file in directory."""
    return max(glob.glob(path + "/*"), key=os.path.getctime)


def mebank_transactions(
    username: str, password: str, account: str, savedir: str, headless: bool
) -> str:
    """Download ME Bank transactions and returns path to saved file."""
    # Set webdriver options (no download popup)
    options = webdriver.firefox.options.Options()
    Path(savedir).mkdir(parents=True, exist_ok=True)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", savedir)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/csv")
    if headless:
        options.add_argument("--headless")
    driver = GeckoDriverManager().install()
    service = Service(executable_path=driver, log_path="/dev/null")
    browser = webdriver.Firefox(service=service, options=options)
    browser.get("https://ib.mebank.com.au/authR5/ib/login.jsp")

    # Login
    print("Logging in...")
    find(browser, By.ID, "username").send_keys(username)
    find(browser, By.ID, "password").send_keys(password)
    find(browser, By.NAME, "auth").click()

    # Navigate to transactions
    print("Transactions page...")
    find(browser, By.CLASS_NAME, "menu-accounts").click()
    find(browser, By.XPATH, ".//*[text()='View transactions']").click()

    # Navigate to account
    print(account + "...")
    iframe = find(browser, By.CSS_SELECTOR, "iframe")
    browser.switch_to.frame(iframe)
    find(browser, By.XPATH, ".//span[text()='Select an account']/..").click()
    find(browser, By.XPATH, f".//*[text()='{account}']").click()

    # Set to last two years
    print("Last two years...")
    find(browser, By.XPATH, ".//span[text()='The last week']/..").click()
    find(browser, By.XPATH, ".//div[text()='The last two years']").click()

    # Go to export PDF page
    print("Export page...")
    while True:
        try:
            break_cond = browser.find_elements(
                By.XPATH, ".//span[text()='Portable document format (PDF)']/.."
            )
            if len(break_cond) > 0:
                break
            find(browser, By.XPATH, ".//a[text()='Export all']").click()
        except Exception:
            continue

    # Download CSV
    print("Download csv...")
    while True:
        try:
            find(
                browser, By.XPATH, ".//span[text()='Portable document format (PDF)']/.."
            ).click()
            find(
                browser, By.XPATH, ".//div[text()='Comma separated values (CSV)']"
            ).click()
            num_downloads = len(glob.glob(savedir + "/*"))
            find(browser, By.XPATH, ".//a[text()='Export']").click()
            break
        except Exception:
            print("Retrying...")

    # Wait for file and rename file
    while len(glob.glob(savedir + "/*")) == num_downloads:
        continue
    time.sleep(2)
    account = "_".join(account.split()).lower()
    old_path = newest_file(savedir)
    new_path = Path(old_path).parent / f"{account}_{Path(old_path).name}"
    os.rename(old_path, new_path)
    print(f"Finished! Saved to {new_path}")
    return new_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument(
        "--account",
        default="Everyday Transaction Account",
        choices=["Everyday Transaction Account", "Online Savings Account"],
    )
    parser.add_argument("--savedir", default=str(Path.cwd() / "downloads"))
    parser.add_argument("--headless", default=True)
    args = parser.parse_args()
    mebank_transactions(
        args.username, args.password, args.account, args.savedir, args.headless
    )
