import urllib.request
import urllib.parse
import re

url = "https://html.duckduckgo.com/html/"
data = urllib.parse.urlencode({'q': '"Dallas College" "inclusive access" OR "first day" OR "equitable access" OR "day one" textbooks'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded'
})
html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')

# Extracting URLs from DuckDuckGo HTML
matches = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)
print("Result URLs found:")
for m in matches:
    print(m)
