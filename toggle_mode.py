import os

MODE_FILE = "post_mode.txt"

def get_next_platform(override_platform: str = "") -> str:
    """
    バリューコマース連携待機中のため、デフォルトは確実に成果報酬の入る「rakuten」固定。
    環境変数 POST_PLATFORM または post_mode.txt が 'yahoo' の場合、あるいは
    override_platform が 'yahoo' の場合のみ Yahoo を使用可能。
    """
    if override_platform in ["rakuten", "yahoo"]:
        return override_platform
    
    # 明示的な指定がなければ楽天のみで運用
    return "rakuten"

def save_current_platform(platform: str):
    """実行したプラットフォームを記録"""
    try:
        with open(MODE_FILE, "w", encoding="utf-8") as f:
            f.write(platform)
    except Exception as e:
        print(f"Failed to save mode file: {e}")
