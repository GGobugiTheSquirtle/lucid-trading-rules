"""Selenium scraper for Lucid Trading Help Center articles."""
import json, time, sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

URLS = [
    # Rules & Guidelines collection
    "https://support.lucidtrading.com/en/collections/12931279-rules-and-guidelines",
    # Individual articles
    "https://support.lucidtrading.com/en/articles/11404732-trade-with-integrity",
    "https://support.lucidtrading.com/en/articles/11404728-permitted-activities",
    "https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times",
    "https://support.lucidtrading.com/en/articles/11404617-maximum-number-of-accounts",
    "https://support.lucidtrading.com/en/articles/11404636-restricted-countries",
    "https://support.lucidtrading.com/en/articles/11404734-prohibited-hedging",
    "https://support.lucidtrading.com/en/articles/11404742-prohibited-microscalping",
    "https://support.lucidtrading.com/en/articles/11404632-inactivity-policy",
    "https://support.lucidtrading.com/en/articles/13425130-new-live-structure",
    "https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts",
    "https://support.lucidtrading.com/en/articles/13891785-lucidmaxx",
    "https://support.lucidtrading.com/en/articles/13424897-lucidblack-payout-objectives",
    "https://support.lucidtrading.com/en/articles/12890092-lucidpro-payouts",
    "https://support.lucidtrading.com/en/articles/12890164-luciddirect-payout-objectives",
    "https://support.lucidtrading.com/en/articles/12890029-lucidpro-evaluation-account",
    "https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account",
    "https://support.lucidtrading.com/en/articles/12890069-lucidpro-funded-account",
    "https://support.lucidtrading.com/en/articles/12890122-lucidpro-daily-loss-limit",
]

# Also try to discover more articles from the collection page
EXTRA_DISCOVER = True

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def extract_page(driver, url, retries=2):
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(3)

            # Try to find Intercom article content
            content = ""
            title = ""

            # Get title
            try:
                title_el = driver.find_element(By.CSS_SELECTOR, "h1, .t__h1, [data-testid='article-title']")
                title = title_el.text.strip()
            except:
                try:
                    title = driver.title.strip()
                except:
                    title = url.split("/")[-1]

            # Try multiple content selectors
            selectors = [
                ".intercom-force-break",
                ".article__body",
                "[data-testid='article-content']",
                ".article-body",
                ".c__body",
                "article",
                ".content",
                "main",
            ]

            for sel in selectors:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        content = "\n\n".join(e.text.strip() for e in els if e.text.strip())
                        if len(content) > 50:
                            break
                except:
                    continue

            # Fallback: get body text
            if len(content) < 50:
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                except:
                    pass

            return {"url": url, "title": title, "content": content, "status": "ok"}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return {"url": url, "title": "", "content": "", "status": f"error: {str(e)}"}

def discover_articles(driver, collection_url):
    """Try to find all article links from the collection page."""
    found = []
    try:
        driver.get(collection_url)
        time.sleep(4)

        # Scroll down to load all
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/articles/']")
        for link in links:
            href = link.get_attribute("href")
            if href and "/articles/" in href and href not in found:
                found.append(href)
    except Exception as e:
        print(f"[discover] error: {e}", file=sys.stderr)
    return found

def main():
    print("Setting up Chrome driver...", file=sys.stderr)
    driver = setup_driver()
    results = []

    all_urls = list(URLS)

    # Discover extra articles from collection page
    if EXTRA_DISCOVER:
        print("Discovering articles from collection page...", file=sys.stderr)
        discovered = discover_articles(driver, URLS[0])
        for u in discovered:
            if u not in all_urls:
                all_urls.append(u)
                print(f"  [discovered] {u}", file=sys.stderr)

    print(f"\nTotal {len(all_urls)} URLs to scrape.\n", file=sys.stderr)

    for i, url in enumerate(all_urls):
        print(f"[{i+1}/{len(all_urls)}] {url.split('/')[-1][:60]}...", file=sys.stderr)
        result = extract_page(driver, url)
        results.append(result)
        print(f"  -> {result['status']} | title: {result['title'][:60]} | len: {len(result['content'])}", file=sys.stderr)

    driver.quit()

    # Output JSON to file
    with open("scraped_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Done! Saved to scraped_results.json", file=sys.stderr)

if __name__ == "__main__":
    main()
