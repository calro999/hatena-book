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
                    items.append({
                        "title": item_data.get("title"),
                        "itemCaption": item_data.get("itemCaption", ""),
                        "affiliateUrl": item_data.get("affiliateUrl"),
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

def main():
    print("=== Starting Rakuten Kobo Hatena Blog Poster ===")
    
    # 1. Configurations
    rakuten_app_id = os.environ.get("RAKUTEN_APP_ID", "DUMMY_APP_ID")
    rakuten_access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    rakuten_affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "DUMMY_AFFILIATE_ID")
    
    hatena_id = os.environ.get("HATENA_ID", "DUMMY_HATENA_ID")
    blog_id = os.environ.get("HATENA_BLOG_ID", "book-muryo.hateblo.jp")
    hatena_api_key = os.environ.get("HATENA_API_KEY", "")

    dry_run = not hatena_api_key or hatena_api_key.startswith("DUMMY")
    if dry_run:
        print("Warning: HATENA_API_KEY is not set. Running in DRY-RUN/DEMO mode.")

    # 2. Genre Table (Mapped by JST hour: 0-23)
    # koboGenreId values:
    #   101101: 少年コミック, 101102: 少女コミック, 101103: 青年コミック, 101104: レディースコミック
    #   101211: BL, 101212: TL
    #   101901: 小説・ノンフィクション, 101903: ライトノベル
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

    # 3. Determine Initial Genre by Current JST Hour
    timezone_jst = datetime.timezone(datetime.timedelta(hours=9))
    now_jst = datetime.datetime.now(timezone_jst)
    current_hour = now_jst.hour
    print(f"Current Time (JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')} (Hour: {current_hour})")

    selected_genre = genre_table.get(current_hour, genre_table[0])
    genre_id = selected_genre["genre_id"]
    keyword = selected_genre["keyword"]
    genre_name = selected_genre["genre_name"]
    display_name = selected_genre["display_name"]
    category = selected_genre["category"]
    
    print(f"JST Hour {current_hour} -> Initial Selected Genre: {display_name} (GenreId: {genre_id}, Keyword: {keyword})")

    # 4. Load Cache
    posted_cache = load_cache()
    print(f"Loaded {len(posted_cache)} posted items from cache.")

    # 5. Fetch and Filter Loop (with fallback)
    target_item = None
    max_retries = 5
    current_genre_id = genre_id
    current_keyword = keyword
    current_sort = "-releaseDate"

    for attempt in range(max_retries + 1):
        print(f"--- Attempt {attempt} (Genre: {current_genre_id}, Keyword: '{current_keyword}', Sort: {current_sort}) ---")
        items = fetch_kobo_items(rakuten_app_id, rakuten_access_key, rakuten_affiliate_id, current_genre_id, current_keyword, sort=current_sort)
        
        if items:
            print(f"Fetched {len(items)} items. Checking for new items...")
            for item in items:
                item_num = item.get("itemNumber")
                if item_num and item_num not in posted_cache:
                    target_item = item
                    break
            
            if target_item:
                print(f"Found new item: {target_item['title']}")
                break
            else:
                print("All fetched items in this query have already been posted.")
        else:
            print("No items fetched for this query.")
        
        # Setup fallback parameters for the next attempt
        if attempt < max_retries:
            # Alternate search options: Choose a random genre from the table
            fallback_hour = random.choice(list(genre_table.keys()))
            fallback_genre = genre_table[fallback_hour]
            current_genre_id = fallback_genre["genre_id"]
            current_keyword = fallback_genre["keyword"]
            genre_name = fallback_genre["genre_name"]
            display_name = fallback_genre["display_name"]
            category = fallback_genre["category"]
            
            # Alternate sorting between sales, standard, and releaseDate
            current_sort = random.choice(["-releaseDate", "sales", "standard"])
            print(f"Switching to fallback settings: {display_name} sorted by {current_sort}")

    if not target_item:
        print("Error: Could not find any unposted items after all retries.")
        sys.exit(0)

    print(f"Selected Item to Post: {target_item['title']} (Number: {target_item['itemNumber']})")

    # 6. Generate Eyecatch Image
    print("Generating Eyecatch Image...")
    img_gen = ImageGenerator()
    eyecatch_path = "eyecatch.png"
    img_gen.generate_eyecatch(
        prompt=target_item["title"],
        output_path=eyecatch_path,
        category=category
    )

    # 7. Generate Article Content (Mapping to hatena-mono interface)
    print("Generating Article Content using LLM...")
    article_gen = ArticleGenerator()
    article_gen.load_model()
    
    title_raw = target_item["title"]
    import re
    clean_title = re.sub(r'【[^】]+】|\[[^\]]+\]', '', title_raw).strip()

    # Construct the features list from itemCaption for article_generator.py to parse
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

    # 8. Setup Hatena Client and Upload Eyecatch
    hatena_client = HatenaAPI(
        hatena_id=hatena_id,
        blog_id=blog_id,
        api_key=hatena_api_key
    )

    uploaded_image_url = hatena_client.upload_image_to_fotolife(eyecatch_path)
    if not uploaded_image_url:
        print("Fotolife upload failed or skipped. Using Unsplash fallback in HTML.")
        uploaded_image_url = img_gen._select_unsplash_image_url(
            target_item["title"], 
            category=category
        )

    # Translate synopsis to Japanese and wrap in a styled div (avoiding blockquote overlap)
    print("Translating/formatting synopsis...")
    translated_synopsis = article_gen.translate_synopsis(target_item['itemCaption'])

    # Construct HTML article
    img_html = f'<div style="text-align: center; margin: 20px 0;"><img src="{uploaded_image_url}" alt="{target_item["title"]}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.08);"></div>'
    
    synopsis_html = f"""<h3>公式あらすじ</h3>
<div style="background: #f9f9f9; padding: 18px 20px; border-left: 5px solid #0099FF; margin: 20px 0; line-height: 1.6; color: #444; border-radius: 0 8px 8px 0; font-size: 15px;">
{translated_synopsis}
</div>"""

    cta_html = f"""<div style="text-align: center; margin: 40px 0 20px 0;">
    <a href="{target_item['affiliateUrl']}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: #0099FF; color: #fff; padding: 16px 32px; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 30px; box-shadow: 0 4px 15px rgba(0,153,255,0.3); text-align: center;">
        ＼ 今すぐ無料で試し読みする ／
    </a>
</div>"""

    # Combine all parts (GA tag removed as requested)
    article_content = f"{img_html}\n{llm_section}\n\n{synopsis_html}\n\n{cta_html}"

    # Generate appropriate blog title depending on genre
    if genre_name == "漫画":
        blog_title = f"【新刊情報】『{clean_title}』が発売開始！最新巻のあらすじ・見どころまとめ"
    elif "ライトノベル" in display_name or "ラノベ" in display_name:
        blog_title = f"【新作ラノベ】『{clean_title}』の見どころ・あらすじ紹介！本日より配信スタート"
    else:
        blog_title = f"【新作小説】『{clean_title}』の見どころ・あらすじ紹介！本日より配信スタート"

    # 9. Post to Hatena Blog
    success = hatena_client.post_entry(
        title=blog_title,
        content=article_content,
        is_draft=False
    )

    if success:
        print("Successfully posted to Hatena Blog!")
        if not dry_run:
            save_cache(target_item["itemNumber"])
            print(f"Added {target_item['itemNumber']} to posted cache.")
    else:
        print("Failed to post entry.")
        sys.exit(1)

    print("=== Auto Post Process Completed! ===")

if __name__ == "__main__":
    main()
