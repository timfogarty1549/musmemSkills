#!/usr/bin/env python3
"""
fetch_img2.py — Download img2 for a specific scorecard post on demand.

Use this when img1 did not contain date/location info. Fetches the second
scorecard image (PNG or JPG) and saves it to /tmp/scorecards/<slug>-img2.{ext}.

Usage:
    python3 fetch_img2.py <post_url>

Output:
    <local_image_path>   (or nothing if no valid img2 found)
"""

import os
import re
import sys
import gzip
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUT_DIR = "/tmp/scorecards"


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        if resp.info().get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data.decode("utf-8", errors="replace")


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def url_exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def slug_from_url(post_url):
    parts = post_url.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else parts[-1]


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <post_url>", file=sys.stderr)
        sys.exit(1)

    post_url = sys.argv[1]
    slug = slug_from_url(post_url)

    html = fetch_html(post_url)
    m = re.search(r'class[= ]"?entry-content"?>(.*?)</(?:div|footer)', html, re.DOTALL)
    content = m.group(1) if m else html
    found = re.findall(r'data-src=(https://[^\s"\']+\.(?:png|jpe?g))', content, re.IGNORECASE)

    if not found:
        print(f"# No images found at {post_url}", file=sys.stderr)
        sys.exit(0)

    # Build list of candidate URLs starting from index 1 (img2)
    first_url = found[0]
    ext = re.search(r'\.(png|jpe?g)$', first_url, re.IGNORECASE).group(0)
    page1_url = re.sub(r'-(\d+)\.(png|jpe?g)$', f'-1{ext}', first_url, flags=re.IGNORECASE)
    if page1_url != first_url and url_exists(page1_url):
        found = [page1_url] + found

    # img2 is index 1 in the full list
    if len(found) < 2:
        print(f"# No img2 available for {post_url}", file=sys.stderr)
        sys.exit(0)

    img2_url = found[1]
    img2_ext = re.search(r'\.(png|jpe?g)$', img2_url, re.IGNORECASE).group(0)
    os.makedirs(OUT_DIR, exist_ok=True)
    local_path = os.path.join(OUT_DIR, f"{slug}-img2{img2_ext}")

    img_bytes = fetch_bytes(img2_url)
    if not (img_bytes.startswith(b'\x89PNG\r\n\x1a\n') or img_bytes.startswith(b'\xff\xd8\xff')):
        print(f"# WARNING: img2 returned non-image content", file=sys.stderr)
        sys.exit(0)

    with open(local_path, "wb") as f:
        f.write(img_bytes)

    print(local_path)


if __name__ == "__main__":
    main()
