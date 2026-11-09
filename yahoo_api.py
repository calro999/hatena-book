import os
import re
import random
import requests
from typing import List, Dict, Any, Optional

def clean_yahoo_book_title(title: str) -> str:
    """Yahoo!ショッピングの書籍・コミックタイトルをクレンジング"""
    if not title:
        return "注目コミック・書籍"

    cleaned = title
    brackets = [
        r'\{[^}]*\}', r'【[^】]*】', r'\[[^\]]*\]', r'［[^］]*］',
        r'（[^）]*）', r'\([^)]*\)', r'〈[^〉]*〉', r'《[^》]*》',
        r'〔[^〕]*〕'
    ]
    for b in brackets:
        cleaned = re.sub(b, ' ', cleaned)

    cleaned = re.sub(r'[★☆◆◇■□▲▼◎○〇♪!！?？※・]+', ' ', cleaned)

    promo_words = [
        r'送料無料.*', r'あすつく', r'即納', r'ポイント\s*\d+倍', r'PayPay\s*\d+倍',
        r'新品', r'全巻セット', r'全巻', r'予約', r'コミックセット', r'セット'
    ]
    for pw in promo_words:
        cleaned = re.sub(pw, ' ', cleaned, flags=re.IGNORECASE)

    delimiters = [r'\s*\|\s*', r'\s*｜\s*', r'\s*／\s*', r'\s*/\s*', r'\s*－\s*', r'\s*:\s*', r'\s*：\s*']
    for delim in delimiters:
        parts = re.split(delim, cleaned)
        if parts and len(parts[0].strip()) >= 3:
            cleaned = parts[0]
            break

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:30].strip() or title[:20].strip()

class YahooBookAPI:
    """Yahoo!ショッピング API (v3) - 書籍・コミック・ラノベ用"""
    
    BASE_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    
    BOOK_KEYWORDS = [
        ("少年コミック 話題作", "manga"),
        ("青年コミック おすすめ", "manga"),
        ("少女コミック 人気", "manga"),
        ("ライトノベル 異世界", "novel"),
        ("話題の小説 文芸", "novel"),
        ("ミステリー小説 傑作", "novel"),
        ("ファンタジー コミック 新刊", "manga"),
        ("SF小説 おすすめ", "novel"),
        ("ビジネス書 ベストセラー", "book"),
        ("日常系 コミック", "manga")
    ]

    def __init__(self, client_id: str = "", affiliate_id: str = ""):
        self.client_id = client_id or os.environ.get("YAHOO_CLIENT_ID", "")
        self.affiliate_id = affiliate_id or os.environ.get("YAHOO_AFFILIATE_ID", "")

    def generate_random_query(self) -> tuple:
        return random.choice(self.BOOK_KEYWORDS)

    def search_items(self, query: str = "", hits: int = 30) -> List[Dict[str, Any]]:
        if not self.client_id:
            print("Warning: YAHOO_CLIENT_ID is not configured.")
            return []

        cat_hint = "book"
        if not query:
            query, cat_hint = self.generate_random_query()

        params = {
            "appid": self.client_id,
            "query": query,
            "results": min(hits, 30),
            "sort": "-score",
            "in_stock": "true",
            "image_size": 600
        }

        if self.affiliate_id:
            params["affiliate_type"] = "vc"
            params["affiliate_id"] = self.affiliate_id

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                items = []
                for raw in data.get("hits", []):
                    title = raw.get("name", "")
                    clean_title = clean_yahoo_book_title(title)
                    price_val = raw.get("price", 0)
                    price_str = f"{price_val:,}円" if isinstance(price_val, (int, float)) else str(price_val)

                    image_url = ""
                    ex_img = raw.get("exImage")
                    if isinstance(ex_img, dict) and ex_img.get("url"):
                        image_url = ex_img.get("url")
                    elif isinstance(raw.get("image"), dict):
                        image_url = raw.get("image", {}).get("medium") or raw.get("image", {}).get("small", "")

                    item_url = raw.get("url", "")
                    item_code = raw.get("code") or raw.get("id") or item_url

                    items.append({
                        "title": title,
                        "clean_title": clean_title,
                        "itemCaption": raw.get("description", "") or f"話題の人気作『{clean_title}』。読者の心を掴む魅力的なストーリー展開が楽しめます。",
                        "affiliateUrl": item_url,
                        "imageUrl": image_url,
                        "price": price_str,
                        "itemNumber": f"yahoo_{item_code}",
                        "category": cat_hint,
                        "platform": "yahoo"
                    })
                return items
            else:
                print(f"Yahoo Book API error {resp.status_code}: {resp.text[:150]}")
                return []
        except Exception as e:
            print(f"Yahoo Book API request failed: {e}")
            return []
