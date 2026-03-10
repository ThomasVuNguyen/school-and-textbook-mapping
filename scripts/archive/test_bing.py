import urllib.request
import urllib.parse
import re

url = "https://www.bing.com/search?q=" + urllib.parse.quote('"Dallas College" "inclusive access" OR "first day" OR "equitable access" OR "day one" textbooks')
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})

try:
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    matches = re.findall(r'<a[^>]+href="([^"]+)"', html)
    print(f"Total links: {len(matches)}")
    for m in matches:
        if "dallascollege.edu" in m or ".edu" in m or "bkstr" in m:
            print(m)
except Exception as e:
    print(e)
