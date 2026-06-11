import os
import sys
import datetime
import urllib.request
import urllib.parse
import urllib.error
import json
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

def fetch_kobo_items(app_id: str, affiliate_id: str, genre_id: str, keyword: str) -> list:
    """Fetches items from Rakuten Kobo Ebook Search API."""
    if not app_id or app_id.startswith("DUMMY"):
        print("Rakuten App ID not set. Using mock data for local dry-run.")
        return get_mock_items(genre_id)

    base_url = "https://app.rakuten.co.jp/services/api/Kobo/EbookSearch/20170426"
    params = {
        "applicationId": app_id,
        "affiliateId": affiliate_id,
        "sort": "-releaseDate",
        "hits": 5,
        "koboGenreId": genre_id,
        "format": "json"
    }
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
    rakuten_affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "DUMMY_AFFILIATE_ID")
    
    hatena_id = os.environ.get("HATENA_ID", "DUMMY_HATENA_ID")
    blog_id = os.environ.get("HATENA_BLOG_ID", "DUMMY_BLOG_ID")
    hatena_api_key = os.environ.get("HATENA_API_KEY", "")

    dry_run = not hatena_api_key or hatena_api_key.startswith("DUMMY")
    if dry_run:
        print("Warning: HATENA_API_KEY is not set. Running in DRY-RUN/DEMO mode.")

    # 2. Determine Genre by Current JST Hour
    # Get current time in JST (UTC+9)
    timezone_jst = datetime.timezone(datetime.timedelta(hours=9))
    now_jst = datetime.datetime.now(timezone_jst)
    current_hour = now_jst.hour
    print(f"Current Time (JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')} (Hour: {current_hour})")

    # Odd hour -> Comic. Even hour -> Light Novel.
    if current_hour % 2 != 0:
        genre_id = "101"
        keyword = ""
        genre_name = "漫画"
        print(f"JST Hour {current_hour} (Odd) -> Selected Genre: Comic (GenreId: {genre_id})")
    else:
        genre_id = "101903"
        keyword = "ライトノベル"
        genre_name = "ラノベ・小説"
        print(f"JST Hour {current_hour} (Even) -> Selected Genre: Light Novel (GenreId: {genre_id}, Keyword: {keyword})")

    # 3. Load Cache
    posted_cache = load_cache()
    print(f"Loaded {len(posted_cache)} posted items from cache.")

    # 4. Fetch Items
    items = fetch_kobo_items(rakuten_app_id, rakuten_affiliate_id, genre_id, keyword)
    if not items:
        print("Error: No items fetched from Rakuten Kobo API.")
        sys.exit(1)

    print(f"Fetched {len(items)} items. Checking for new items...")

    # 5. Filter Unposted Items (Find the newest unposted item)
    # The API returns items sorted by -releaseDate, so the first unposted item in the list is the newest.
    target_item = None
    for item in items:
        item_num = item.get("itemNumber")
        if item_num and item_num not in posted_cache:
            target_item = item
            break

    if not target_item:
        print("All fetched items have already been posted. Nothing to do today.")
        sys.exit(0)

    print(f"Selected Item to Post: {target_item['title']} (Number: {target_item['itemNumber']})")

    # 6. Generate Eyecatch Image
    print("Generating Eyecatch Image...")
    img_gen = ImageGenerator()
    eyecatch_path = "eyecatch.png"
    img_gen.generate_eyecatch(
        prompt=target_item["title"],
        output_path=eyecatch_path,
        category="novel" if genre_name == "ラノベ・小説" else "manga"
    )

    # 7. Generate Article Content
    print("Generating Article Content using LLM...")
    article_gen = ArticleGenerator()
    article_gen.load_model()
    llm_section = article_gen.generate_review_article(target_item)

    # 8. Setup Hatena Client and Upload Eyecatch
    hatena_client = HatenaAPI(
        hatena_id=hatena_id,
        blog_id=blog_id,
        api_key=hatena_api_key
    )

    uploaded_image_url = hatena_client.upload_image_to_fotolife(eyecatch_path)
    if not uploaded_image_url:
        print("Fotolife upload failed or skipped. Using Unsplash fallback in HTML.")
        # Fallback to an Unsplash image URL
        uploaded_image_url = img_gen._select_unsplash_image_url(
            target_item["title"], 
            category="novel" if genre_name == "ラノベ・小説" else "manga"
        )

    # Construct HTML article
    img_html = f'<div style="text-align: center; margin: 20px 0;"><img src="{uploaded_image_url}" alt="{target_item["title"]}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.08);"></div>'
    
    synopsis_html = f"""
<h3>公式あらすじ</h3>
<blockquote style="background: #f9f9f9; padding: 15px; border-left: 4px solid #0099FF; margin: 20px 0; font-style: italic;">
    {target_item['itemCaption']}
</blockquote>
"""

    cta_html = f"""
<div style="text-align: center; margin: 40px 0 20px 0;">
    <a href="{target_item['affiliateUrl']}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: #0099FF; color: #fff; padding: 16px 32px; font-size: 18px; font-weight: bold; text-decoration: none; border-radius: 30px; box-shadow: 0 4px 15px rgba(0,153,255,0.3); text-align: center;">
        ＼ 今すぐ無料で試し読みする ／
    </a>
</div>
"""

    # Complete Article Body
    article_content = f"{img_html}\n{llm_section}\n{synopsis_html}\n{cta_html}"

    # Determine Title based on genre
    title_raw = target_item["title"]
    import re
    clean_title = re.sub(r'【[^】]+】|\[[^\]]+\]', '', title_raw).strip()

    if genre_name == "漫画":
        blog_title = f"【新刊情報】『{clean_title}』が発売開始！最新巻のあらすじ・見どころまとめ"
    else:
        blog_title = f"【新作ラノベ】『{clean_title}』の見どころ・あらすじ紹介！本日より配信スタート"

    # 9. Post to Hatena Blog
    success = hatena_client.post_entry(
        title=blog_title,
        html_content=article_content,
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
