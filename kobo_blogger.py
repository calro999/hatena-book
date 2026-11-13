from typing import Optional, Set, Dict, Any
import time
import base64
import tempfile
from playwright.sync_api import sync_playwright
import os
import sys
import datetime
import urllib.request
import urllib.parse
import urllib.error
import json
import random
import time
import requests
from hatena_api import HatenaAPI
from article_generator import ArticleGenerator
from image_generator import ImageGenerator
from yahoo_api import YahooBookAPI
from toggle_mode import get_next_platform, save_current_platform

CACHE_FILE = "posted_cache.txt"

def load_cache() -> set:
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def save_cache(item_number: str):
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{item_number}\n")

def fetch_kobo_items(app_id: str, access_key: str, affiliate_id: str, genre_id: str, keyword: str, sort: str = "-releaseDate") -> list:
    """Fetches items from the latest Rakuten Kobo Ebook Search API."""
    if not app_id or app_id.startswith("DUMMY"):
        print("Rakuten App ID not set. Using mock data for local dry-run.")
        return get_mock_items(genre_id)

    print(f"Debug: RAKUTEN_APP_ID length is {len(app_id)}")

    base_url = "https://openapi.rakuten.co.jp/services/api/Kobo/EbookSearch/20170426"
    params = {
        "applicationId": app_id,
        "affiliateId": affiliate_id,
        "sort": sort,
        "hits": 30,
        "koboGenreId": genre_id,
        "format": "json"
    }
    
    if access_key:
        print(f"Debug: RAKUTEN_ACCESS_KEY is set. Length: {len(access_key)}")
        params["accessKey"] = access_key
    if keyword:
        params["keyword"] = keyword

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    try:
        print(f"Requesting Rakuten Kobo API: {url.split('applicationId=')[0]}applicationId=***")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            items = []
            for entry in data.get("Items", []):
                item_data = entry.get("Item", {})
                if item_data:
                    base_item_url = item_data.get("itemUrl")
                    if not base_item_url:
                        aff_url = item_data.get("affiliateUrl") or ""
                        base_item_url = aff_url.split("?")[0] if aff_url else ""

                    final_affiliate_url = item_data.get("affiliateUrl")
                    if affiliate_id and not affiliate_id.startswith("DUMMY") and base_item_url:
                        encoded_pc_url = urllib.parse.quote(base_item_url)
                        final_affiliate_url = f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={encoded_pc_url}"

                    items.append({
                        "title": item_data.get("title"),
                        "itemCaption": item_data.get("itemCaption", ""),
                        "affiliateUrl": final_affiliate_url,
                        "itemNumber": item_data.get("itemNumber"),
                        "releaseDate": item_data.get("releaseDate")
                    })
            return items
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
            print(f"Failed to fetch from Rakuten Kobo API (HTTPError): {e}")
            print(f"Error Response Body: {error_body}")
        except Exception:
            print(f"Failed to fetch from Rakuten Kobo API (HTTPError): {e}")
        return []
    except Exception as e:
        print(f"Failed to fetch from Rakuten Kobo API: {e}")
        return []

def get_mock_items(genre_id: str) -> list:
    """Returns mock data based on genre for testing/dry-run."""
    if genre_id == "101":
        return [
            {
                "title": "テストコミック新刊 1巻",
                "itemCaption": "大人気ファンタジーコミックの最新刊！主人公が新たな世界で最強のスキルを手に入れ、仲間と共に魔王に立ち向かう冒険活劇。笑いあり涙ありの超話題作が遂に登場！",
                "affiliateUrl": "https://r18.afl.rakuten.co.jp/mock_comic",
                "itemNumber": "mock_comic_001",
                "releaseDate": "2026-06-12"
            }
        ]
    else:
        return [
            {
                "title": "テストライトノベル新書 1巻",
                "itemCaption": "異世界転生した主人公が、現代の知識と魔法を使って理想のセカンドライフを築き上げる。立ちはだかる困難を機転と魔法で解決していく爽快ファンタジー小説！",
                "affiliateUrl": "https://r18.afl.rakuten.co.jp/mock_novel",
                "itemNumber": "mock_novel_001",
                "releaseDate": "2026-06-12"
            }
        ]

def post_single_article(
    post_index: int,
    total_posts: int,
    posted_cache: set,
    hatena_client: HatenaAPI,
    article_gen: ArticleGenerator,
    img_gen: ImageGenerator,
    genre_table: dict,
    rakuten_app_id: str,
    rakuten_access_key: str,
    rakuten_affiliate_id: str,
    yahoo_client: Optional[YahooBookAPI],
    forced_platform: str,
    dry_run: bool
) -> bool:
    print(f"\n==================================================")
    print(f"=== Starting Book Post Batch [{post_index}/{total_posts}] ===")
    print(f"==================================================")

    platform = get_next_platform(forced_platform)
    print(f"Selected Platform for Post #{post_index}: {platform.upper()}")

    # Determine Genre by Current JST Hour (with offset for post 2 to vary genres)
    timezone_jst = datetime.timezone(datetime.timedelta(hours=9))
    now_jst = datetime.datetime.now(timezone_jst)
    target_hour = (now_jst.hour + (post_index - 1) * 3) % 24
    print(f"Target JST Hour for post #{post_index}: {target_hour}")

    selected_genre = genre_table.get(target_hour, genre_table[0])
    genre_id = selected_genre["genre_id"]
    keyword = selected_genre["keyword"]
    genre_name = selected_genre["genre_name"]
    display_name = selected_genre["display_name"]
    category = selected_genre["category"]

    target_item = None
    max_retries = 5

    if platform == "yahoo" and yahoo_client:
        print("--- Fetching items from Yahoo! Shopping (Books) ---")
        for attempt in range(max_retries + 1):
            q, cat_hint = yahoo_client.generate_random_query()
            print(f"--- Attempt {attempt} (Yahoo Query: '{q}') ---")
            items = yahoo_client.search_items(query=q, hits=30)
            if items:
                random.shuffle(items)
                for item in items:
                    item_num = item.get("itemNumber")
                    if item_num and item_num not in posted_cache:
                        target_item = item
                        category = item.get("category", "book")
                        display_name = "話題の書籍・コミック"
                        genre_name = "漫画" if category == "manga" else "小説"
                        break
            if target_item:
                break
    else:
        if platform == "yahoo" and not yahoo_client:
            print("YAHOO_CLIENT_ID not found. Falling back to Rakuten.")
            platform = "rakuten"
        print("--- Fetching items from Rakuten Kobo ---")
        current_genre_id = genre_id
        current_keyword = keyword
        current_sort = "-releaseDate"

        for attempt in range(max_retries + 1):
            print(f"--- Attempt {attempt} (Genre: {current_genre_id}, Keyword: '{current_keyword}', Sort: {current_sort}) ---")
            items = fetch_kobo_items(rakuten_app_id, rakuten_access_key, rakuten_affiliate_id, current_genre_id, current_keyword, sort=current_sort)
            
            if items:
                for item in items:
                    item_num = item.get("itemNumber")
                    if item_num and item_num not in posted_cache:
                        target_item = item
                        break
                if target_item:
                    break
            
            if attempt < max_retries:
                fallback_hour = random.choice(list(genre_table.keys()))
                fallback_genre = genre_table[fallback_hour]
                current_genre_id = fallback_genre["genre_id"]
                current_keyword = fallback_genre["keyword"]
                genre_name = fallback_genre["genre_name"]
                display_name = fallback_genre["display_name"]
                category = fallback_genre["category"]
                current_sort = random.choice(["-releaseDate", "sales", "standard"])

    if not target_item:
        print(f"Warning: Could not find any unposted items for Post #{post_index}.")
        return False

    print(f"Selected Item to Post: {target_item['title']} (Number: {target_item['itemNumber']})")

    # Eyecatch Image
    eyecatch_path = f"eyecatch_{post_index}.png"
    img_gen.generate_eyecatch(
        prompt=target_item["title"],
        output_path=eyecatch_path,
        category=category
    )

    # Article Generation
    title_raw = target_item["title"]
    import re
    cleaned = re.sub(r'\{[^}]*\}|【[^】]*】|\[[^\]]*\]|［[^］]*］|（[^）]*）|\([^)]*\)|〈[^〉]*〉|《[^》]*》', ' ', title_raw)
    cleaned = re.sub(r'[★☆◆◇■□▲▼◎○〇♪!！?？※]+', ' ', cleaned)
    cleaned = re.sub(r'送料無料|あす楽|即納|電子書籍|楽天Kobo|コミック|小説', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    clean_title = cleaned[:25].strip() if len(cleaned) > 25 else cleaned
    if not clean_title:
        clean_title = title_raw[:20].strip()

    excerpt = target_item['itemCaption'][:150] + "..." if len(target_item['itemCaption']) > 150 else target_item['itemCaption']
    mapped_features = [
        f"最新刊・注目作品『{clean_title}』の配信スタート",
        f"あらすじ・見どころ: {excerpt}"
    ]
    
    generator_input_item = {
        "title": target_item["title"],
        "clean_title": clean_title,
        "features": mapped_features,
        "price": "電子書籍版",
        "url": target_item["affiliateUrl"]
    }
    
    llm_section = article_gen.generate_review_article(generator_input_item)

    uploaded_image_url = hatena_client.upload_image_to_fotolife(eyecatch_path)
    if not uploaded_image_url:
        uploaded_image_url = img_gen._select_unsplash_image_url(
            target_item["title"], 
            category=category
        )

    translated_synopsis = article_gen.translate_synopsis(target_item['itemCaption'])

    img_html = f'<div style="text-align: center; margin: 20px 0;"><img src="{uploaded_image_url}" alt="{target_item["title"]}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.08);"></div>'

    synopsis_html = f"""<h3>公式あらすじ</h3>
<div style="background: #f9f9f9; padding: 18px 20px; border-left: 5px solid #0099FF; margin: 20px 0; line-height: 1.6; color: #444; border-radius: 0 8px 8px 0; font-size: 15px;">
{translated_synopsis}
</div>"""

    if platform == "yahoo":
        cta_text = f"＼ Yahoo!ショッピングで『{clean_title}』を見る 🛒 ／"
        cta_btn = "linear-gradient(135deg, #ff0033 0%, #ff334b 100%)"
        cta_shadow = "rgba(255,0,51,0.3)"
    else:
        cta_text = "＼ 楽天Koboで今すぐ試し読みする 📖 ／"
        cta_btn = "#0099FF"
        cta_shadow = "rgba(0,153,255,0.3)"

    cta_html = f"""<div style="text-align: center; margin: 40px 0 20px 0;">
    <a href="{target_item['affiliateUrl']}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: {cta_btn}; color: #fff; padding: 16px 32px; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 30px; box-shadow: 0 4px 15px {cta_shadow}; text-align: center;">
        {cta_text}
    </a>
</div>"""

    raw_article = f"{llm_section}\n\n{synopsis_html}\n\n{cta_html}"
    
    import markdown
    html_body = markdown.markdown(raw_article, extensions=['nl2br', 'tables'])
    
    def add_target_blank(match):
        tag = match.group(0)
        if 'target=' not in tag:
            tag = tag.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ')
        return tag
        
    html_body = re.sub(r'<a\s+[^>]*>', add_target_blank, html_body)
    article_content = f"{img_html}\n{html_body}"

    # タイトルのテンプレート重複を防止し自然なバリエーションを生成
    title_templates = [
        f"『{clean_title}』の見どころと魅力を徹底解説！今すぐ読みたいおすすめポイントまとめ",
        f"話題の注目作『{clean_title}』をピックアップ！あらすじとおすすめポイント紹介",
        f"『{clean_title}』配信スタート！物語の見どころと注目ポイントまとめ",
        f"一気読み必至！『{clean_title}』のあらすじと見どころを分かりやすく解説"
    ]
    blog_title = random.choice(title_templates)

    success = hatena_client.post_entry(
        title=blog_title,
        content=article_content,
        is_draft=False
    )

    if success:
        print(f"Successfully posted Post #{post_index} to Hatena Blog!")
        if not dry_run:
            save_cache(target_item["itemNumber"])
            posted_cache.add(target_item["itemNumber"])
            print(f"Added {target_item['itemNumber']} to posted cache.")
        save_current_platform(platform)
        print(f"Rotated platform state: last was {platform}")

        if os.path.exists(eyecatch_path):
            try:
                os.remove(eyecatch_path)
            except Exception:
                pass

        return True
    else:
        print(f"Failed to post entry for Post #{post_index}.")
        return False

def main():
    print("=== Starting Rakuten Kobo Hatena Blog Poster ===")
    
    # 1. Configurations
    rakuten_app_id = os.environ.get("RAKUTEN_APP_ID", "DUMMY_APP_ID")
    rakuten_access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    rakuten_affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "DUMMY_AFFILIATE_ID")

    yahoo_client_id = os.environ.get("YAHOO_CLIENT_ID", "")
    yahoo_affiliate_id = os.environ.get("YAHOO_AFFILIATE_ID", "")
    
    hatena_id = os.environ.get("HATENA_ID", "DUMMY_HATENA_ID")
    blog_id = os.environ.get("HATENA_BLOG_ID", "book-muryo.hateblo.jp")
    hatena_api_key = os.environ.get("HATENA_API_KEY", "")

    forced_platform = os.environ.get("POST_PLATFORM", "").strip().lower()

    dry_run = not hatena_api_key or hatena_api_key.startswith("DUMMY")
    if dry_run:
        print("Warning: HATENA_API_KEY is not set. Running in DRY-RUN/DEMO mode.")

    genre_table = {
        0: {"genre_id": "101", "keyword": "少年コミック", "genre_name": "漫画", "display_name": "少年コミック", "category": "manga"},
        1: {"genre_id": "101", "keyword": "少女コミック", "genre_name": "漫画", "display_name": "少女コミック", "category": "manga"},
        2: {"genre_id": "101", "keyword": "青年コミック", "genre_name": "漫画", "display_name": "青年コミック", "category": "manga"},
        3: {"genre_id": "101903", "keyword": "", "genre_name": "ラノベ・小説", "display_name": "ライトノベル", "category": "novel"},
        4: {"genre_id": "101901", "keyword": "ミステリー", "genre_name": "ラノベ・小説", "display_name": "ミステリー小説", "category": "novel"},
        5: {"genre_id": "101", "keyword": "BL", "genre_name": "漫画", "display_name": "BL (ボーイズラブ)", "category": "manga"},
        6: {"genre_id": "101", "keyword": "TL", "genre_name": "漫画", "display_name": "TL (ティーンズラブ)", "category": "manga"},
        7: {"genre_id": "101", "keyword": "少年コミック ファンタジー", "genre_name": "漫画", "display_name": "少年ファンタジー漫画", "category": "manga"},
        8: {"genre_id": "101", "keyword": "少女コミック 恋愛", "genre_name": "漫画", "display_name": "少女恋愛漫画", "category": "manga"},
        9: {"genre_id": "101", "keyword": "青年コミック アクション", "genre_name": "漫画", "display_name": "青年アクション漫画", "category": "manga"},
        10: {"genre_id": "101903", "keyword": "異世界", "genre_name": "ラノベ・小説", "display_name": "異世界ライトノベル", "category": "novel"},
        11: {"genre_id": "101901", "keyword": "SF", "genre_name": "ラノベ・小説", "display_name": "SFファンタジー小説", "category": "novel"},
        12: {"genre_id": "101", "keyword": "少年コミック", "genre_name": "漫画", "display_name": "少年コミック", "category": "manga"},
        13: {"genre_id": "101", "keyword": "少女コミック", "genre_name": "漫画", "display_name": "少女コミック", "category": "manga"},
        14: {"genre_id": "101", "keyword": "青年コミック", "genre_name": "漫画", "display_name": "青年コミック", "category": "manga"},
        15: {"genre_id": "101903", "keyword": "", "genre_name": "ラノベ・小説", "display_name": "ライトノベル", "category": "novel"},
        16: {"genre_id": "101901", "keyword": "ホラー", "genre_name": "ラノベ・小説", "display_name": "ホラー・サスペンス小説", "category": "novel"},
        17: {"genre_id": "101", "keyword": "BL", "genre_name": "漫画", "display_name": "BL (ボーイズラブ)", "category": "manga"},
        18: {"genre_id": "101", "keyword": "TL", "genre_name": "漫画", "display_name": "TL (ティーンズラブ)", "category": "manga"},
        19: {"genre_id": "101", "keyword": "少年コミック 冒険", "genre_name": "漫画", "display_name": "少年冒険漫画", "category": "manga"},
        20: {"genre_id": "101", "keyword": "少女コミック ファンタジー", "genre_name": "漫画", "display_name": "少女ファンタジー漫画", "category": "manga"},
        21: {"genre_id": "101", "keyword": "青年コミック SF", "genre_name": "漫画", "display_name": "青年SF漫画", "category": "manga"},
        22: {"genre_id": "101903", "keyword": "ラブコメ", "genre_name": "ラノベ・小説", "display_name": "ラブコメライトノベル", "category": "novel"},
        23: {"genre_id": "101901", "keyword": "推理", "genre_name": "ラノベ・小説", "display_name": "推理小説・ミステリー", "category": "novel"},
    }

    posted_cache = load_cache()
    print(f"Loaded {len(posted_cache)} posted items from cache.")

    yahoo_client = None
    if yahoo_client_id:
        yahoo_client = YahooBookAPI(client_id=yahoo_client_id, affiliate_id=yahoo_affiliate_id)

    hatena_client = HatenaAPI(
        hatena_id=hatena_id,
        blog_id=blog_id,
        api_key=hatena_api_key
    )

    img_gen = ImageGenerator()
    article_gen = ArticleGenerator()
    article_gen.load_model()

    posts_per_run = int(os.environ.get("POSTS_PER_RUN", "2"))
    successful_posts = 0

    for idx in range(1, posts_per_run + 1):
        success = post_single_article(
            post_index=idx,
            total_posts=posts_per_run,
            posted_cache=posted_cache,
            hatena_client=hatena_client,
            article_gen=article_gen,
            img_gen=img_gen,
            genre_table=genre_table,
            rakuten_app_id=rakuten_app_id,
            rakuten_access_key=rakuten_access_key,
            rakuten_affiliate_id=rakuten_affiliate_id,
            yahoo_client=yahoo_client,
            forced_platform=forced_platform,
            dry_run=dry_run
        )
        if success:
            successful_posts += 1

        if idx < posts_per_run:
            print(f"Waiting 15 seconds before next post...")
            time.sleep(15)

    print(f"\n=== Auto Post Process Completed: {successful_posts}/{posts_per_run} posts published successfully ===")
    if successful_posts == 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
