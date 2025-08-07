import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time

start_url = "past any website url"

visited = set()
to_visited = [start_url]

sitemap_urls = []

while to_visited:
    url = to_visited.pop(0)
    if url in visited or urlparse(url).netloc != urlparse(start_url).netloc:
        continue

    try: 
        response = requests.get(url)
        if response.status_code != 200:
            continue
    except:
        continue

    visited.add(url)
    sitemap_urls.append(url)

    soup = BeautifulSoup(response.text, 'html.parser')
    for link in soup.find_all('a', href=True):
        full_url = urljoin(url, link['href'].split('#')[0])
        if full_url.startswith(start_url) and full_url not in visited:
            to_visited.append(full_url)

    time.sleep(1)


with open("sitemap.xml", 'w', encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')   
    for url in sitemap_urls:
        f.write(f"  <url><loc>{url}</loc></url>\n")
    f.write('</urlset>\n')

print(f"Sitemap generation complete. {len(sitemap_urls)} pages saved in sitemap.xml")
