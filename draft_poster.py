import os
import sys
import random
from typing import Set
from yahoo_researcher import YahooResearcher
from article_formatter_draft import DraftArticleFormatter
from hatena_api import HatenaAPI

CACHE_FILE = "draft_cache.txt"

def load_cache() -> Set[str]:
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_cache(code: str):
    if not code:
        return
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{code}\n")

def main():
    print("=== Starting Hatena Draft Article Generator ===")

    # 1. Load Configurations
    yahoo_client_id = os.environ.get("YAHOO_CLIENT_ID", "")
    hatena_id = os.environ.get("HATENA_ID", "")
    blog_id = os.environ.get("HATENA_BLOG_ID", "")
    hatena_api_key = os.environ.get("HATENA_API_KEY", "")

    # Target genre or specific search keyword
    # options for target_blog: mono (gadget), mikke (hobby), book (books)
    target_genre = os.environ.get("TARGET_GENRE", "mono").strip().lower()
    search_query = os.environ.get("SEARCH_QUERY", "").strip()

    if not yahoo_client_id:
        print("Error: YAHOO_CLIENT_ID is required.")
        sys.exit(1)

    if not hatena_api_key:
        print("Warning: HATENA_API_KEY is not set. Running in DRY-RUN mode.")

    hatena_client = HatenaAPI(
        hatena_id=hatena_id,
        blog_id=blog_id,
        api_key=hatena_api_key
    )

    # 2. Research Unposted Unique Item from Yahoo! Shopping
    researcher = YahooResearcher(client_id=yahoo_client_id)
    cache = load_cache()
    print(f"Loaded {len(cache)} items from cache.")

    target_item = None
    max_retries = 8

    for attempt in range(max_retries):
        if search_query and attempt == 0:
            query = search_query
        else:
            query = researcher.get_random_query(target_genre)

        print(f"--- Attempt {attempt + 1}/{max_retries} (Query: '{query}') ---")
        items = researcher.search_items(query=query, hits=25)
        if not items:
            continue

        random.shuffle(items)
        for item in items:
            code = item.get("item_code", "")
            if code and code not in cache:
                target_item = item
                break
        if target_item:
            break

    if not target_item:
        print("Error: Could not find any unique unposted items.")
        sys.exit(1)

    print(f"Selected Item: {target_item['clean_name']} ({target_item['price']}) - Code: {target_item['item_code']}")

    # 3. Generate HTML Review Article in Specified Format
    formatter = DraftArticleFormatter()
    title, article_html = formatter.generate_article(
        item=target_item,
        placeholder_affiliate_url=target_item.get("url", "")
    )

    print(f"Generated Draft Title: {title}")

    # 4. Post as DRAFT (is_draft=True) to Hatena Blog
    # はてなブログAPIの is_draft=True により、記事は公開されず「下書き」にのみ保存されます。
    entry_url = hatena_client.post_entry(
        title=title,
        html_content=article_html,
        is_draft=True
    )

    if entry_url:
        print(f"Successfully saved as DRAFT to Hatena Blog! Draft Entry: {entry_url}")
        save_cache(target_item["item_code"])
        print("=== Draft Generation Completed Successfully ===")
    else:
        print("Failed to save draft entry to Hatena Blog.")
        sys.exit(1)

if __name__ == "__main__":
    main()
