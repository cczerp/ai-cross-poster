from playwright.sync_api import sync_playwright
from utils.logger import log

def get_browser(headless=True):
    log("Launching browser...")
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    return pw, browser, context, page
