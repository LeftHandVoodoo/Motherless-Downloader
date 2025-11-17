from __future__ import annotations

import sys
import httpx
from downloader.discover import discover_media_url


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: probe_motherless.py <url>")
        return 2
    url = sys.argv[1]
    if url.startswith('@'):
        url = url[1:]
    headers = {"User-Agent": "Mozilla/5.0", "Referer": url}
    with httpx.Client(timeout=10.0, headers=headers, follow_redirects=True) as client:
        r = client.head(url)
        print("HEAD on page:", r.status_code)
        for k, v in r.headers.items():
            print(k, ":", v)
        if r.status_code not in (200, 206):
            g = client.get(url)
            print("GET page:", g.status_code)
            media = discover_media_url(g.text) if g.status_code == 200 else None
            print("Discovered media:", media)
            if media:
                r2 = client.head(media)
                print("HEAD on media:", r2.status_code)
                for k, v in r2.headers.items():
                    print(k, ":", v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
