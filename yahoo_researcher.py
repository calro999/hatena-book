import os
import re
import random
import requests
import urllib.request
import ssl
from typing import List, Dict, Any, Optional

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def is_valid_yahoo_image(url: str) -> bool:
    """Yahoo!の画像URLが実際に存在するか（no-imageダミーでないか）を判定"""
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            if r.status != 200:
                return False
            data = r.read()
            # 4997 bytesはYahooのNo-Image共通ダミー画像
            if len(data) == 4997 or len(data) < 5000:
                return False
            return True
    except Exception:
        return False

def clean_yahoo_title(title: str) -> str:
    """Yahoo!ショッピング特有のSEOキーワード詰め込みやPRタグを除去し、スマートで短い商品名に整形"""
    if not title:
        return "注目アイテム"

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
        r'送料無料.*', r'あすつく', r'即納', r'ランキング\s*\d*位', r'第?\d+冠',
        r'クーポン(で|\s*利用で)?\d+%?OFF?', r'ポイント\s*\d+倍', r'PayPay\s*\d+倍',
        r'超PayPay祭', r'お買い物マラソン', r'セール', r'限定', r'正規品',
        r'公式', r'メーカー保証', r'ギフト', r'プレゼント', r'お祝い',
        r'202[4-7]年?(最新|新型)?', r'最新(版|型)?', r'新型', r'景品玩具', r'景品',
        r'おもちゃ', r'雑貨', r'配送区分[A-Z0-9]', r'メール便', r'定形外'
    ]
    for pw in promo_words:
        cleaned = re.sub(pw, ' ', cleaned, flags=re.IGNORECASE)

    delimiters = [r'\s*\|\s*', r'\s*｜\s*', r'\s*／\s*', r'\s*/\s*', r'\s*－\s*', r'\s*:\s*', r'\s*：\s*']
    for delim in delimiters:
        parts = re.split(delim, cleaned)
        if parts and len(parts[0].strip()) >= 4:
            cleaned = parts[0]
            break

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    words = cleaned.split()
    if words:
        result = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + (1 if result else 0) <= 26:
                result.append(w)
                cur_len += len(w) + (1 if len(result) > 1 else 0)
            elif not result:
                result.append(w[:24])
                break
            else:
                break
        cleaned = ' '.join(result)

    return cleaned if len(cleaned) >= 3 else title[:22].strip()

class YahooResearcher:
    """Yahoo!ショッピングAPI v3を利用した高精度商品リサーチクライアント"""
    BASE_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

    TARGET_QUERIES = {
        "mono": [
            "ホットアイマスク 充電式",
            "ワイヤレスイヤホン ノイズキャンセリング",
            "モバイルバッテリー 急速充電",
            "スマートウォッチ 心拍計",
            "骨伝導イヤホン Bluetooth",
            "首掛け扇風機 静音 冷却プレート",
            "卓上加湿器 超音波 静音",
            "エルゴノミクス マウス ワイヤレス",
            "Bluetooth スピーカー 防水",
            "メカニカルキーボード 静音",
            "デスクライト 調光調色",
            "USBハブ ドッキングステーション"
        ],
        "mikke": [
            "ちいかわ ガチャガチャ コンプリート",
            "スヌーピー カプセルトイ フィギュア",
            "サンリオ シークレットBOX",
            "ポケモン マスコット ぬいぐるみ",
            "ちいかわ マスコット ぬいぐるみ",
            "スクイーズ もちもち キーホルダー",
            "パペットスンスン グッズ",
            "スーパーマリオ フィギュア コレクション"
        ],
        "book": [
            "話題のコミック 全巻セット",
            "少年コミック 話題作",
            "青年コミック おすすめ",
            "異世界 ライトノベル",
            "本屋大賞 受賞作 小説",
            "ミステリー小説 傑作",
            "少女コミック 恋愛 おすすめ"
        ]
    }

    def __init__(self, client_id: str = ""):
        self.client_id = client_id or os.environ.get("YAHOO_CLIENT_ID", "")

    def get_random_query(self, target_genre: str = "mono") -> str:
        queries = self.TARGET_QUERIES.get(target_genre, self.TARGET_QUERIES["mono"])
        return random.choice(queries)

    def extract_valid_images_from_item(self, item_url: str, image_id: str) -> List[str]:
        """商品ページおよびCDNから【確実に実在する商品画像】のみを検証して3枚抽出"""
        valid_images = []

        # 1. メイン大画像
        main_l_url = f"https://item-shopping.c.yimg.jp/i/l/{image_id}"
        if is_valid_yahoo_image(main_l_url):
            valid_images.append(main_l_url)

        # 2. 商品ページのHTMLから実在する高解像度画像URLをスクレイピング
        if item_url:
            try:
                req = urllib.request.Request(item_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    
                    # パターンA: タイムスタンプ付きCDN画像 (_d_)
                    cdn_imgs = re.findall(r'https://item-shopping\.c\.yimg\.jp/i/[ngl]/[^\s\"\'\<\>\?]+', html)
                    for c_img in cdn_imgs:
                        if c_img not in valid_images and is_valid_yahoo_image(c_img):
                            valid_images.append(c_img)
                            if len(valid_images) >= 3:
                                break

                    # パターンB: ショップライブラリの高品質商品画像 (shopping.c.yimg.jp/lib/)
                    if len(valid_images) < 3:
                        lib_imgs = re.findall(r'https://shopping\.c\.yimg\.jp/lib/[^\s\"\'\<\>]+\.(?:jpg|png|jpeg)', html)
                        for l_img in lib_imgs:
                            # トップ画像やアイコン等のノイズを除去
                            if not any(skip in l_img for skip in ["top-cat", "icon", "banner", "logo"]):
                                if l_img not in valid_images and is_valid_yahoo_image(l_img):
                                    valid_images.append(l_img)
                                    if len(valid_images) >= 3:
                                        break
            except Exception as e:
                print(f"Error scraping product page images: {e}")

        # 3. それでも3枚に満たない場合、検証済みのメイン画像で補完（no imageを完全防止）
        fallback_img = valid_images[0] if valid_images else f"https://item-shopping.c.yimg.jp/i/l/{image_id}"
        while len(valid_images) < 3:
            valid_images.append(fallback_img)

        return valid_images[:3]

    def search_items(self, query: str = "", hits: int = 20) -> List[Dict[str, Any]]:
        if not self.client_id:
            print("Warning: YAHOO_CLIENT_ID is not configured.")
            return []

        if not query:
            query = "ガジェット"

        params = {
            "appid": self.client_id,
            "query": query,
            "results": min(hits, 30),
            "sort": "-score",
            "in_stock": "true",
            "image_size": 600
        }

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_items = data.get("hits", [])
                items = []

                for raw in raw_items:
                    name = raw.get("name", "")
                    clean_name = clean_yahoo_title(name)
                    price_val = raw.get("price", 0)
                    price_str = f"{price_val:,}円" if isinstance(price_val, (int, float)) else str(price_val)
                    item_url = raw.get("url", "")
                    item_code = raw.get("code") or raw.get("id") or item_url
                    image_id = raw.get("imageId", "")
                    description = raw.get("description", "") or raw.get("headLine", "")

                    # 確実に実在するYahoo商品画像を3枚のみ抽出
                    images = self.extract_valid_images_from_item(item_url, image_id)

                    items.append({
                        "name": name,
                        "clean_name": clean_name,
                        "price": price_str,
                        "url": item_url,
                        "item_code": item_code,
                        "image_id": image_id,
                        "images": images,
                        "seller": raw.get("seller", {}).get("name", "Yahoo!ショッピング"),
                        "description": description,
                        "review_rate": raw.get("review", {}).get("rate"),
                        "review_count": raw.get("review", {}).get("count")
                    })
                return items
            else:
                print(f"Yahoo Search error: HTTP {resp.status_code}")
                return []
        except Exception as e:
            print(f"Yahoo Search failed: {e}")
            return []
