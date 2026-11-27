import os
import sys
import time
import json
import base64
import urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.expanduser("~/.config/affiliate_browser_profile")
COOKIE_FILE = os.path.join(USER_DATA_DIR, "cookies.json")

class AffiliateBrowserExtractor:
    """
    Yahoo!ショッピングの商品ページから公式アフィリエイトリンクを取得するクラス。
    - ローカルPC実行時: 保存されたChromeプロファイルまたはcookies.jsonを使用
    - GitHub Actions実行時: 環境変数 YAHOO_COOKIES_JSON (Base64または生JSON) をPlaywrightに注入
    """
    def __init__(self, user_data_dir: str = USER_DATA_DIR, headless: bool = True):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.amazon_associate_tag = os.environ.get("AMAZON_ASSOCIATE_TAG", "mattan0290c-22")
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)

    def _get_launch_args(self):
        return [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars"
        ]

    def _load_cookies(self, context):
        """ローカルファイルまたは環境変数からCookieを注入"""
        cookies = []
        env_cookies = os.environ.get("YAHOO_COOKIES_JSON", "")
        if env_cookies:
            try:
                try:
                    decoded = base64.b64decode(env_cookies).decode("utf-8")
                    cookies = json.loads(decoded)
                except Exception:
                    cookies = json.loads(env_cookies)
            except Exception as e:
                print(f"[Cookie] Warning parsing YAHOO_COOKIES_JSON: {e}")

        if not cookies and os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
            except Exception as e:
                print(f"[Cookie] Warning reading {COOKIE_FILE}: {e}")

        if cookies:
            try:
                context.add_cookies(cookies)
                print(f"[Cookie] Successfully loaded {len(cookies)} cookies.")
            except Exception as e:
                print(f"[Cookie] Warning adding cookies: {e}")

    def get_yahoo_affiliate_url(self, item_url: str, timeout_sec: int = 15) -> str:
        """Yahoo!ショッピングの商品ページから公式短縮アフィリエイトリンクを取得"""
        with sync_playwright() as p:
            # GitHub ActionsなどのヘッドレスLinux環境か、ローカルChrome環境かを自動判定
            is_github_actions = "GITHUB_ACTIONS" in os.environ
            
            if is_github_actions:
                browser = p.chromium.launch(
                    headless=True,
                    args=self._get_launch_args()
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
                self._load_cookies(context)
            else:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    channel="chrome",
                    viewport={"width": 1280, "height": 800},
                    args=self._get_launch_args(),
                    ignore_default_args=["--enable-automation"]
                )
                self._load_cookies(context)

            page = context.pages[0] if context.pages else context.new_page()
            context.grant_permissions(["clipboard-read", "clipboard-write"])

            try:
                print(f"[Yahoo Browser] Navigating: {item_url}")
                page.goto(item_url, wait_until="domcontentloaded", timeout=timeout_sec * 1000)
                time.sleep(1.5)

                share_btn = page.locator("#affrt_br-button button, button:has-text('共有')")
                if share_btn.count() > 0 and share_btn.first.is_visible():
                    print("[Yahoo Browser] Clicking share button...")
                    share_btn.first.click()
                    time.sleep(1.0)

                    copy_btn = page.locator("button:has-text('リンクをコピー'), button:has-text('コピー')")
                    if copy_btn.count() > 0 and copy_btn.first.is_visible():
                        copy_btn.first.click()
                        time.sleep(0.5)
                        clip_url = page.evaluate("navigator.clipboard.readText()")
                        if clip_url and ("yahoo.jp" in clip_url or "shopping.yahoo.co.jp" in clip_url):
                            print(f"[Yahoo Browser] Successfully obtained official affiliate URL: {clip_url}")
                            context.close()
                            return clip_url.strip()

            except Exception as e:
                print(f"[Yahoo Browser] Warning during extraction: {e}")
            finally:
                context.close()

        print("[Yahoo Browser] Fallback to original URL.")
        return item_url

    def get_amazon_search_url(self, clean_title: str) -> str:
        """Amazon公式アソシエイト検索URL"""
        encoded_query = urllib.parse.quote(clean_title)
        return f"https://www.amazon.co.jp/s?k={encoded_query}&tag={self.amazon_associate_tag}"

if __name__ == "__main__":
    extractor = AffiliateBrowserExtractor()
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://store.shopping.yahoo.co.jp/huaweistore/55037246.html"
    print("Yahoo Affiliate:", extractor.get_yahoo_affiliate_url(test_url))
    print("Amazon Affiliate:", extractor.get_amazon_search_url("HUAWEI FreeClip 2"))
