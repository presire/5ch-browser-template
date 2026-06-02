"""bbspink.org/ex0ch/ への投稿フロー調査.

デフォルトはフォーム構造のみダンプ (実投稿なし)。
実際に POST して挙動を見たい場合は明示的に --really-post を付ける。
注意: ex0ch は confirm 段階がなく 1 回の POST で書き込みが完了するため、
--really-post を渡すと本当に書き込みが発生する。

実行: python scripts/probe_bbspink_post_flow.py            # safe / form のみ
      python scripts/probe_bbspink_post_flow.py --really-post  # 実投稿
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Tuple
from urllib.parse import urljoin

import requests

UA = "Monazilla/1.00 Ember/0.1"
TIMEOUT = 15

THREAD_URL = "https://bbspink.org/ex0ch/test/read.cgi/operate/1775635309/"


def decode(body: bytes) -> str:
    for enc in ("shift_jis", "cp932", "utf-8"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("shift_jis", errors="replace")


def show_form(html: str, base: str) -> Tuple[str, list, list]:
    form_match = re.search(r"<form[^>]+action=[\"']?([^\"'> ]+)[\"']?[^>]*>(.*?)</form>", html, re.IGNORECASE | re.DOTALL)
    if not form_match:
        print("  no <form> found")
        return "", [], []
    action = urljoin(base, form_match.group(1))
    body = form_match.group(2)
    inputs = re.findall(r'<input[^>]+>', body, flags=re.IGNORECASE)
    fields = []
    for tag in inputs:
        name = re.search(r'name=["\']?([^"\'> ]+)', tag)
        value = re.search(r'value=["\']?([^"\'>]*)', tag)
        typ = re.search(r'type=["\']?([^"\'> ]+)', tag)
        if name:
            fields.append((name.group(1), value.group(1) if value else "", typ.group(1) if typ else "text"))
    textareas = re.findall(r'<textarea[^>]*name=["\']?([^"\'> ]+)', body, flags=re.IGNORECASE)
    return action, fields, textareas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--really-post",
        action="store_true",
        help="実際に POST を発行する (デフォルトはフォーム構造ダンプのみ)",
    )
    args = parser.parse_args()

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    print(f"[1/4] GET thread: {THREAD_URL}")
    r = s.get(THREAD_URL, timeout=TIMEOUT)
    print(f"  status={r.status_code} bytes={len(r.content)} ctype={r.headers.get('Content-Type','-')}")
    print(f"  set-cookie: {r.headers.get('Set-Cookie','-')[:200]}")
    html = decode(r.content)

    print("[2/4] Locate post form on thread page")
    action, fields, textareas = show_form(html, THREAD_URL)
    print(f"  action: {action}")
    print(f"  textareas: {textareas}")
    print(f"  fields ({len(fields)}):")
    for name, value, typ in fields:
        v = value if len(value) < 60 else value[:60] + "..."
        print(f"    {typ:8s} {name:20s} = {v!r}")

    print("[3/4] POST step")
    if not action:
        print("  skip: no form action")
        return 0
    if not args.really_post:
        print("  skip: --really-post not given (default is safe / no actual POST)")
        print("  NOTE: ex0ch has no confirm step — any POST writes immediately.")
        return 0
    post_data = {n: v for n, v, _ in fields}
    post_data.update({
        "FROM": "",
        "mail": "sage",
        "MESSAGE": "probe (do not post)",
        "submit": "書き込む",
    })
    referer = THREAD_URL
    print(f"  POST {action}  referer={referer}")
    headers = {"Referer": referer, "Content-Type": "application/x-www-form-urlencoded"}
    body = "&".join(f"{k}={v}" for k, v in post_data.items())
    body_bytes = body.encode("shift_jis", errors="replace")
    rp = s.post(action, data=body_bytes, headers=headers, timeout=TIMEOUT, allow_redirects=False)
    print(f"  -> status={rp.status_code} ctype={rp.headers.get('Content-Type','-')} loc={rp.headers.get('Location','-')[:100]}")
    print(f"  -> set-cookie: {rp.headers.get('Set-Cookie','-')[:200]}")
    rp_html = decode(rp.content)
    print(f"  -> body preview (first 600 chars):")
    print("    " + re.sub(r"\s+", " ", rp_html[:600]))

    print("[4/4] Identify confirm form in response (if 5ch-style)")
    if "confirm" in rp_html.lower() or "クッキー" in rp_html or "確認" in rp_html or "もう一度" in rp_html or "BBS_PROXY" in rp_html.upper():
        print("  confirm-style page detected")
        a2, f2, t2 = show_form(rp_html, action)
        print(f"  confirm action: {a2}")
        print(f"  confirm fields ({len(f2)}):")
        for name, value, typ in f2[:20]:
            v = value if len(value) < 60 else value[:60] + "..."
            print(f"    {typ:8s} {name:20s} = {v!r}")
    else:
        print("  no confirm step detected (may have posted directly or was rejected outright)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
