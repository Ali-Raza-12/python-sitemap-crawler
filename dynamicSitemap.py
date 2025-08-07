"""
WEB CRAWLER & SITEMAP GENERATOR
Corrected Version - Fixes issue with skipping initial URL
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import time
import logging
import datetime
from diskcache import Cache

# ====================== CONFIG ======================
START_URL = "past any website url"
DOMAIN = urlparse(START_URL).netloc
CRAWL_DELAY = 1
MAX_RETRIES = 3
MAX_URLS = 1000
MAX_DEPTH = 3

DISALLOWED_EXTENSIONS = ('.jpg', '.png', '.gif', '.svg', '.pdf', '.docx', '.zip', '.mp4', '.webp')
CHANGEFREQ = "weekly"
PRIORITY = "0.5"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ====================== LOGGING & INIT ======================
print("=== INITIALIZING CRAWLER ===")
print(f"Target Website: {START_URL}")
print(f"Domain: {DOMAIN}")

logging.basicConfig(
    filename="sitemap_crawler.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ====================== ROBOTS.TXT ======================
robots = RobotFileParser()
robots_url = urljoin(START_URL, "/robots.txt")
robots.set_url(robots_url)
try:
    robots.read()
    print(f"robots.txt fetched: {robots_url}")
except Exception as e:
    print(f"⚠️ Could not read robots.txt: {e}")

def is_allowed(url):
    try:
        allowed = robots.can_fetch("*", url)
        if not allowed:
            print(f"🚫 Blocked by robots.txt: {url}")
        return allowed
    except:
        return True

# ====================== SELENIUM SETUP ======================
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"user-agent={USER_AGENT}")
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(30)
print("✅ Chrome WebDriver initialized")

# ====================== CACHE ======================
cache = Cache('crawl_cache')
# Uncomment to clear previous crawl
# cache.clear()
# print("🧼 Cache cleared")

# ====================== HELPERS ======================
def normalize_url(url):
    url = url.split('#')[0].rstrip('/').lower()
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    return url

def should_crawl(url, depth):
    parsed = urlparse(url)
    if DOMAIN not in parsed.netloc:
        print(f"🌐 External skipped: {url}")
        return False
    if url.endswith(DISALLOWED_EXTENSIONS):
        print(f"📁 File skipped: {url}")
        return False
    if depth > MAX_DEPTH:
        print(f"⬇️ Max depth reached: {url}")
        return False
    if not is_allowed(url):
        return False
    if url in cache:
        print(f"⏩ Already visited (cached): {url}")
        return False
    return True

def get_links_from_page(url, depth):
    print(f"\n📄 Crawling (Depth {depth}): {url}")
    retries = 0
    while retries < MAX_RETRIES:
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )

            # Accept cookies if button exists
            try:
                accept_btn = driver.find_element(By.XPATH, '//button[contains(., "Accept")]')
                accept_btn.click()
                print("✅ Cookies accepted")
                time.sleep(1)
            except:
                pass

            soup = BeautifulSoup(driver.page_source, "html.parser")
            anchors = soup.find_all('a', href=True)
            print(f"🔗 Raw links: {len(anchors)}")

            links = []
            for a in anchors:
                href = a['href'].strip()
                if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                    full = urljoin(url, href)
                    links.append(full)

            print(f"✅ Valid links: {len(links)}")
            return links

        except Exception as e:
            print(f"⚠️ Retry {retries+1} failed: {e}")
            retries += 1
            time.sleep(2 ** retries)
    return []

# ====================== MAIN CRAWL LOOP ======================
to_visit = [(START_URL, 0)]
sitemap_urls = []

while to_visit and len(sitemap_urls) < MAX_URLS:
    current_url, depth = to_visit.pop(0)
    normalized_url = normalize_url(current_url)

    if not should_crawl(normalized_url, depth):
        continue

    # Mark as visited
    cache[normalized_url] = True
    sitemap_urls.append(normalized_url)
    print(f"✅ Added: {normalized_url}")

    links = get_links_from_page(current_url, depth)
    for link in links:
        norm_link = normalize_url(link)
        if should_crawl(norm_link, depth + 1):
            to_visit.append((norm_link, depth + 1))

    time.sleep(CRAWL_DELAY)

# ====================== CLEANUP ======================
driver.quit()
cache.close()
print("🧹 Browser and cache closed")

# ====================== SITEMAP GENERATION ======================
print(f"\n🗂️ Generating sitemap for {len(sitemap_urls)} URLs...")
def generate_sitemap(urls):
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for url in urls:
            f.write("  <url>\n")
            f.write(f"    <loc>{url}</loc>\n")
            f.write(f"    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n")
            f.write(f"    <changefreq>{CHANGEFREQ}</changefreq>\n")
            f.write(f"    <priority>{PRIORITY}</priority>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")

generate_sitemap(sitemap_urls)
print("✅ Sitemap written to sitemap.xml")
