import os

MODE_FILE = "post_mode.txt"

def get_next_platform(override_platform: str = "") -> str:
    """
    楽天とYahooを交互に実行する（楽天 ⇄ Yahoo）。
    override_platform が指定されていればそれを優先。
    """
    if override_platform in ["rakuten", "yahoo"]:
        return override_platform
    
    current_mode = "rakuten"
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content in ["rakuten", "yahoo"]:
                    current_mode = content
        except Exception:
            pass

    # 交互に切り替え: 前回がrakutenなら次はyahoo、前回がyahooなら次はrakuten
    next_platform = "yahoo" if current_mode == "rakuten" else "rakuten"
    return next_platform

def save_current_platform(platform: str):
    """実行したプラットフォームを記録"""
    try:
        with open(MODE_FILE, "w", encoding="utf-8") as f:
            f.write(platform)
    except Exception as e:
        print(f"Failed to save mode file: {e}")

