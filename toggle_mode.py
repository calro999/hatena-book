import os

MODE_FILE = "post_mode.txt"

def get_next_platform(override_platform: str = "") -> str:
    """楽天とYahooを1回ずつ交互に切り替える（13楽天 + 13Yahoo = 26回/日）"""
    if override_platform in ["rakuten", "yahoo"]:
        return override_platform
    
    current_mode = "yahoo"
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip().lower()
                if content == "rakuten":
                    current_mode = "yahoo"
                else:
                    current_mode = "rakuten"
        except Exception:
            current_mode = "rakuten"
    else:
        current_mode = "rakuten"
        
    return current_mode

def save_current_platform(platform: str):
    """実行したプラットフォームを記録"""
    try:
        with open(MODE_FILE, "w", encoding="utf-8") as f:
            f.write(platform)
    except Exception as e:
        print(f"Failed to save mode file: {e}")
