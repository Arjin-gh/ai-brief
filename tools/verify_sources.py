#!/usr/bin/env python3
"""
verify_sources.py — HEAD-check every URL in a brief.json and annotate
each article with `link_status` (ok | broken) and `verified_at`.

Usage:
    python tools/verify_sources.py brief.json [--timeout 10]

Modifies brief.json in place. Broken URLs still stay in the file — the HTML
template will show a red '⚠️ 链接不可达' badge on those cards.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

USER_AGENT = (
    "Mozilla/5.0 (compatible; ai-brief/1.0; +https://github.com/)"
    " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def check_url(url: str, timeout: float = 10.0) -> tuple[str, int | None]:
    """Return ('ok', status) or ('broken', status_or_None)."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return "broken", None
    except Exception:
        return "broken", None

    for method in ("HEAD", "GET"):
        req = Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(req, timeout=timeout) as resp:
                status = resp.status
                if 200 <= status < 400:
                    return "ok", status
        except HTTPError as e:
            if 200 <= e.code < 400:
                return "ok", e.code
            if method == "HEAD" and e.code in (403, 405, 501):
                continue  # some servers reject HEAD; retry with GET
            return "broken", e.code
        except (URLError, TimeoutError, Exception):
            if method == "HEAD":
                continue  # try GET
            return "broken", None
    return "broken", None


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify URLs in brief.json.")
    ap.add_argument("brief", type=Path)
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    brief = json.loads(args.brief.read_text(encoding="utf-8"))
    articles = brief.get("articles", [])
    today = date.today().isoformat()

    n_ok, n_broken = 0, 0
    for i, a in enumerate(articles, 1):
        url = a.get("url", "")
        status, code = check_url(url, timeout=args.timeout)
        a["link_status"] = status
        a["verified_at"] = today
        if status == "ok":
            n_ok += 1
        else:
            n_broken += 1
        print(f"[verify_sources] {i:2d}/{len(articles)} [{status}{f' {code}' if code else ''}] {url}",
              file=sys.stderr)

    args.brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[verify_sources] ✓ {n_ok} ok, {n_broken} broken (kept, will show warning badge)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
