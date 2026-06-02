"""bbspink.org/ex0ch/ 外部板の調査スクリプト.

http://bbspink.org/ex0ch/ がどのようなページか、配下にどのような板が
存在するか、subject.txt / SETTING.TXT / dat / bbs.cgi といった
5ch 互換エンドポイントが利用可能かを順にプローブして報告する.

実行: python scripts/probe_bbspink_ex0ch.py
"""

from __future__ import annotations

import re
import sys
from typing import Iterable, List, Tuple
from urllib.parse import urljoin, urlparse

import requests

ROOT_URL = "http://bbspink.org/ex0ch/"
TIMEOUT = 15

USER_AGENTS = [
    "Monazilla/1.00",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Ember/0.0.186 (probe; +https://github.com/kiyohken2000/5ch-browser-template)",
]


def fetch(session: requests.Session, url: str) -> Tuple[int, bytes, dict]:
    response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    return response.status_code, response.content, dict(response.headers)


def try_user_agents(url: str) -> Tuple[requests.Session, int, bytes, dict, str]:
    last_status = 0
    last_body = b""
    last_headers: dict = {}
    last_ua = ""
    for ua in USER_AGENTS:
        session = requests.Session()
        session.headers.update({"User-Agent": ua, "Accept": "*/*"})
        try:
            status, body, headers = fetch(session, url)
        except requests.RequestException as exc:
            print(f"  [UA={ua[:30]}] error: {exc}")
            continue
        print(f"  [UA={ua[:30]}] status={status} bytes={len(body)} ctype={headers.get('Content-Type','-')}")
        if status == 200:
            return session, status, body, headers, ua
        last_status, last_body, last_headers, last_ua = status, body, headers, ua
    return session, last_status, last_body, last_headers, last_ua


def decode_body(body: bytes, headers: dict) -> Tuple[str, str]:
    ctype = headers.get("Content-Type", "").lower()
    m = re.search(r"charset=([\w\-]+)", ctype)
    if m:
        enc = m.group(1).lower()
        try:
            return body.decode(enc, errors="replace"), enc
        except LookupError:
            pass
    for enc in ("shift_jis", "cp932", "utf-8", "euc-jp"):
        try:
            text = body.decode(enc)
            if "�" not in text:
                return text, enc + " (guess)"
        except UnicodeDecodeError:
            continue
    return body.decode("shift_jis", errors="replace"), "shift_jis (fallback)"


def extract_links(html: str, base_url: str) -> List[Tuple[str, str]]:
    pattern = re.compile(r'<a[^>]+href=["\']?([^"\'> ]+)["\']?[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    results: List[Tuple[str, str]] = []
    for href, label in pattern.findall(html):
        absolute = urljoin(base_url, href)
        label_clean = re.sub(r"<[^>]+>", "", label).strip()
        results.append((absolute, label_clean))
    return results


def is_board_candidate(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    path = parsed.path.rstrip("/")
    if not path or path == "/ex0ch":
        return False
    if path.endswith((".html", ".htm", ".txt", ".gif", ".png", ".jpg", ".css", ".js")):
        return False
    return True


def probe_endpoint(session: requests.Session, base: str, suffix: str) -> str:
    target = base.rstrip("/") + "/" + suffix
    try:
        status, body, headers = fetch(session, target)
    except requests.RequestException as exc:
        return f"  {suffix:14s} ERR {exc}"
    text, enc = decode_body(body[:4096], headers)
    head = re.sub(r"\s+", " ", text[:160]).strip()
    return f"  {suffix:14s} status={status} bytes={len(body)} enc={enc} head={head!r}"


def main() -> int:
    print(f"[1/7] GET {ROOT_URL}")
    session, status, body, headers, ua = try_user_agents(ROOT_URL)
    if status != 200:
        print(f"FAILED: could not fetch root (last status={status}). Aborting.")
        return 1
    print(f"OK using UA={ua[:60]}")
    print(f"  Content-Type: {headers.get('Content-Type', '-')}")
    print(f"  Server:       {headers.get('Server', '-')}")

    print("[2/7] Decode HTML")
    html, enc = decode_body(body, headers)
    print(f"  encoding: {enc}")
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        print(f"  <title>: {title_match.group(1).strip()[:120]}")

    print("[3/7] Extract links")
    links = extract_links(html, ROOT_URL)
    print(f"  total links: {len(links)}")
    board_links: List[Tuple[str, str]] = []
    seen = set()
    for url, label in links:
        if not is_board_candidate(url):
            continue
        normalized = url.rstrip("/") + "/"
        if normalized in seen:
            continue
        seen.add(normalized)
        board_links.append((normalized, label))
    print(f"  board-like links: {len(board_links)}")
    for i, (url, label) in enumerate(board_links[:15], start=1):
        print(f"  [{i:2d}] {url}  ({label[:40]})")

    print("[4/7] Probe known endpoints on root")
    for suffix in ("bbsmenu.html", "bbsmenu.json", "SETTING.TXT", "subject.txt"):
        print(probe_endpoint(session, ROOT_URL.rstrip("/"), suffix))

    print("[5/7] Probe subject.txt / SETTING.TXT on top board candidates")
    if not board_links:
        print("  (no board candidates to probe)")
        return 0
    first_board_url = board_links[0][0]
    for url, label in board_links[:3]:
        print(f"-- board: {url} ({label[:40]})")
        for suffix in ("subject.txt", "SETTING.TXT"):
            print(probe_endpoint(session, url, suffix))

    print("[6/7] Inspect bbsmenu.json structure")
    try:
        status, body, headers = fetch(session, ROOT_URL.rstrip("/") + "/bbsmenu.json")
    except requests.RequestException as exc:
        print(f"  ERR {exc}")
    else:
        import json as _json
        text, enc = decode_body(body, headers)
        try:
            data = _json.loads(text)
            keys = list(data.keys())
            print(f"  top-level keys: {keys}")
            ml = data.get("menu_list") or []
            print(f"  menu_list count: {len(ml)}")
            if ml:
                first_cat = ml[0]
                print(f"  first category keys: {list(first_cat.keys())}")
                content = first_cat.get("category_content") or []
                if content:
                    print(f"  first board keys: {list(content[0].keys())}")
                    print(f"  first board sample: {content[0]}")
            for k in ("description", "last_modify", "last_modify_string"):
                if k in data:
                    print(f"  {k}: {data[k]}")
        except Exception as exc:
            print(f"  JSON parse error: {exc}")

    print("[7/7] Probe dat file and bbs.cgi on first board")
    try:
        status, body, headers = fetch(session, first_board_url + "subject.txt")
        text, enc = decode_body(body, headers)
        first_line = text.splitlines()[0] if text.strip() else ""
        key_match = re.match(r"(\d+)\.dat", first_line)
        if key_match:
            key = key_match.group(1)
            dat_url = first_board_url + "dat/" + key + ".dat"
            print(f"  trying dat: {dat_url}")
            status, body, headers = fetch(session, dat_url)
            text, enc = decode_body(body[:512], headers)
            head = re.sub(r"\s+", " ", text[:200]).strip()
            print(f"  dat status={status} bytes={len(body)} enc={enc} head={head!r}")
        else:
            print(f"  could not extract dat key from: {first_line[:100]!r}")
    except requests.RequestException as exc:
        print(f"  ERR {exc}")

    for cgi_url in (
        "https://bbspink.org/test/bbs.cgi",
        "https://bbspink.org/ex0ch/test/bbs.cgi",
        first_board_url + "test/bbs.cgi",
    ):
        try:
            r = session.get(cgi_url, timeout=TIMEOUT, allow_redirects=False)
            print(f"  HEAD-like GET {cgi_url} -> status={r.status_code} loc={r.headers.get('Location','-')[:80]} ctype={r.headers.get('Content-Type','-')}")
        except requests.RequestException as exc:
            print(f"  ERR {cgi_url} {exc}")

    print("DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
