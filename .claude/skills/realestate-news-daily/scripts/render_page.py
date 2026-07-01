#!/usr/bin/env python3
"""
범용 JS 페이지 렌더러 — WebFetch/curl로 막히는 SPA·봇차단 사이트의 렌더링된 텍스트를 가져온다.
국토부(molit), 아실(asil), 호갱노노(hogangnono)처럼 JS 렌더링/리다이렉트로 일반 fetch가 실패하는 소스용.

사이트별 셀렉터에 의존하지 않고 "렌더링된 본문 텍스트"를 통째로 반환한다 → 수집가(LLM)가 거기서 데이터를 추출.
이렇게 하면 사이트 구조가 바뀌어도 잘 깨지지 않는다.

사용법:
  python3 render_page.py --url "<URL>" [--wait-ms 3500] [--selector "본문대기셀렉터"] [--max-chars 12000]
  여러 URL: --url A --url B ...

출력(stdout): 각 URL마다
  ===== URL: <url> =====
  <렌더링된 텍스트 (max-chars 까지)>
실패 시 해당 URL 블록에 "RENDER_FAILED: <이유>" 출력(다른 URL은 계속 진행).
"""
import argparse
import sys
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def render_one(browser, url, wait_ms, selector, max_chars):
    ctx = browser.new_context(
        user_agent=UA,
        locale="ko-KR",
        viewport={"width": 1440, "height": 900},
        extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9"},
    )
    # navigator.webdriver 흔적 제거 (가벼운 스텔스)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if selector:
            try:
                page.wait_for_selector(selector, timeout=15000)
            except Exception:
                pass  # 셀렉터 못 찾아도 본문은 반환 시도
        page.wait_for_timeout(wait_ms)
        text = page.inner_text("body")
        text = "\n".join(line for line in text.splitlines() if line.strip())
        return text[:max_chars]
    finally:
        ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--wait-ms", type=int, default=3500)
    ap.add_argument("--selector", default=None)
    ap.add_argument("--max-chars", type=int, default=12000)
    args = ap.parse_args()

    rc = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        for url in args.url:
            print(f"===== URL: {url} =====")
            try:
                print(render_one(browser, url, args.wait_ms, args.selector, args.max_chars))
            except Exception as e:
                print(f"RENDER_FAILED: {e}")
                rc = 1
            print()
        browser.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
