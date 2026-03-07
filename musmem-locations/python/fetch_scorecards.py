#!/usr/bin/env python3
"""
fetch_scorecards.py — Download img1 scorecard images from npcnewsonline.com.

For each scorecard post on the given listing page, downloads only the first
valid (non-corrupt) scorecard image (PNG or JPG) to /tmp/scorecards/. Use
fetch_img2.py to fetch a second image on demand when img1 does not contain
date/location.

Usage:
    python3 fetch_scorecards.py <page_number>

Output (one entry per line, tab-separated):
    <post_title>\t<post_url>\t<local_image_path>
"""

import gzip
import os
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE_LISTING = "https://npcnewsonline.com/category/contest-scorecards/"
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


def get_listing_posts(page):
    url = BASE_LISTING if page == 1 else f"{BASE_LISTING}page/{page}/"
    print(f"# Fetching listing page {page}: {url}", file=sys.stderr, flush=True)
    html = fetch_html(url)

    matches = re.findall(
        r'<a[^>]+href="(https://npcnewsonline\.com/[^"]+)"[^>]*>([^<]+Official Score Cards[^<]*)</a>',
        html, re.IGNORECASE
    )
    seen = {}
    for post_url, title in matches:
        post_url = post_url.strip()
        if post_url not in seen:
            seen[post_url] = title.strip()
    return [(url, title) for url, title in seen.items()]


def url_exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except Exception:
        return False


def is_valid_image(data):
    """Return True if data starts with PNG or JPEG magic bytes."""
    return data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')


def get_scorecard_image_urls(post_url, max_images=1):
    """Return up to max_images scorecard image URLs (PNG or JPG) for the post."""
    html = fetch_html(post_url)
    m = re.search(r'class[= ]"?entry-content"?>(.*?)</(?:div|footer)', html, re.DOTALL)
    content = m.group(1) if m else html
    found = re.findall(r'data-src=(https://[^\s"\']+\.(?:png|jpe?g))', content, re.IGNORECASE)
    if not found:
        return []

    # If first URL has a numbered suffix, try to prepend -1 if missing
    first_url = found[0]
    ext = re.search(r'\.(png|jpe?g)$', first_url, re.IGNORECASE).group(0)
    page1_url = re.sub(r'-(\d+)\.(png|jpe?g)$', f'-1{ext}', first_url, flags=re.IGNORECASE)
    if page1_url != first_url and url_exists(page1_url):
        found = [page1_url] + found

    return found[:max_images]


def slug_from_url(post_url):
    # e.g. https://npcnewsonline.com/2025-ifbb-oklahoma.../1025184/ -> 2025-ifbb-oklahoma...
    parts = post_url.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else parts[-1]


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <page_number>", file=sys.stderr)
        sys.exit(1)

    try:
        page = int(sys.argv[1])
    except ValueError:
        print("ERROR: page_number must be an integer", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    posts = get_listing_posts(page)
    if not posts:
        print("# No scorecard posts found on that page.", file=sys.stderr)
        sys.exit(0)

    print(f"# Found {len(posts)} posts. Downloading first scorecard image for each...", file=sys.stderr)

    for post_url, title in posts:
        print(f"#   {title}", file=sys.stderr, flush=True)
        try:
            # Try up to 3 source images to find a valid (non-corrupt) first image
            img_urls = get_scorecard_image_urls(post_url, max_images=3)
            if not img_urls:
                print(f"#   WARNING: no images found at {post_url}", file=sys.stderr)
                continue
            slug = slug_from_url(post_url)
            saved_path = None
            for i, img_url in enumerate(img_urls, 1):
                img_bytes = fetch_bytes(img_url)
                if not is_valid_image(img_bytes):
                    print(f"#   WARNING: img{i} returned non-image content, skipping", file=sys.stderr)
                    continue
                ext = re.search(r'\.(png|jpe?g)$', img_url, re.IGNORECASE).group(0)
                local_path = os.path.join(OUT_DIR, f"{slug}-img1{ext}")
                with open(local_path, "wb") as f:
                    f.write(img_bytes)
                saved_path = local_path
                break  # Only download the first valid image
            if not saved_path:
                print(f"#   WARNING: no valid image found for {title}", file=sys.stderr)
                continue
            # Tab-separated: title, post_url, img1_path
            print(f"{title}\t{post_url}\t{saved_path}")
        except Exception as e:
            print(f"#   ERROR: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
