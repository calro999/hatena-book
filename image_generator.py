import os
import requests
import io
import random
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional

class ImageGenerator:
    def __init__(self, model_id: str = ""):
        print("ImageGenerator: Initialized using Unsplash book photo pool + Pillow composition.")

    def load_model(self):
        pass

    def generate_eyecatch(self, prompt: str, output_path: str = "eyecatch.png", image_url: Optional[str] = None, category: Optional[str] = None) -> str:
        # Title clean up
        clean_title = prompt
        # We can clean brackets and simple prefixes/suffixes
        import re
        clean_title = re.sub(r'【[^】]+】|\[[^\]]+\]', '', clean_title).strip()
        
        # 1. Select the best photo from Unsplash
        unsplash_url = self._select_unsplash_image_url(clean_title, category)
        print(f"Selected base image URL: {unsplash_url}")
        
        # 2. Download the image
        bg_img = None
        try:
            print("Downloading background photo...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(unsplash_url, headers=headers, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 5000:
                bg_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                bg_img = bg_img.resize((800, 450), Image.Resampling.LANCZOS)
                print("Successfully downloaded and resized base background image.")
            else:
                print(f"Failed to download background image. Status: {resp.status_code}. Using gradient.")
        except Exception as e:
            print(f"Failed to fetch background photo: {e}. Using gradient.")

        # 3. Compile the final composite image with typography overlays
        return self._generate_composite_image(clean_title, bg_img, output_path)

    def _select_unsplash_image_url(self, title: str, category: Optional[str]) -> str:
        title_lower = title.lower()
        
        # Book/Manga/Novel Unsplash photo pools
        pools = {
            "manga": [
                "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop&q=80"
            ],
            "novel": [
                "https://images.unsplash.com/photo-1474932430478-367db26836c1?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=800&auto=format&fit=crop&q=80"
            ],
            "reading": [
                "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=800&auto=format&fit=crop&q=80"
            ]
        }

        # Check title keywords
        if any(w in title_lower for w in ["コミック", "漫画", "マンガ", "巻", "少年", "少女", "コミックス"]):
            return random.choice(pools["manga"])
        if any(w in title_lower for w in ["ライトノベル", "ラノベ", "小説", "文庫", "ファンタジー"]):
            return random.choice(pools["novel"])

        return random.choice(pools["reading"])

    def _load_font(self, size: int):
        jp_font_paths = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Bold.ttf"),
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
        ]
        for path in jp_font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass

        cached = self._download_noto_sans_jp()
        if cached and os.path.exists(cached):
            try:
                return ImageFont.truetype(cached, size)
            except Exception:
                pass

        fallback_paths = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for path in fallback_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _download_noto_sans_jp(self) -> Optional[str]:
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        font_path = os.path.join(font_dir, "NotoSansJP-Bold.ttf")
        if os.path.exists(font_path):
            return font_path
        try:
            os.makedirs(font_dir, exist_ok=True)
            url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Bold.ttf"
            print("Japanese font not found. Downloading Noto Sans JP...")
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(resp.content)
                print(f"Font saved to: {font_path}")
                return font_path
        except Exception as e:
            print(f"Failed to download font: {e}")
        return None

    def _draw_wrapped_text(self, draw: ImageDraw.ImageDraw, text: str, position: Tuple[int, int], font, max_width: int, fill: Tuple[int, int, int, int]):
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            try:
                bbox = font.getbbox(test_line)
                w = bbox[2] - bbox[0]
            except Exception:
                w = draw.textlength(test_line, font=font)
                
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)

        x, y = position
        try:
            sample_bbox = font.getbbox("A")
            char_height = sample_bbox[3] - sample_bbox[1]
        except Exception:
            char_height = 20
            
        line_spacing = int(char_height * 0.3)
        line_height = char_height + line_spacing
        
        for line in lines[:3]:
            draw.text((x + 2, y + 2), line, fill=(10, 10, 15, 180), font=font)
            draw.text((x, y), line, fill=fill, font=font)
            y += line_height

    def _generate_composite_image(self, clean_title: str, bg_img: Optional[Image.Image], output_path: str, size: Tuple[int, int] = (800, 450)) -> str:
        width, height = size
        
        if bg_img:
            image = bg_img.resize(size, Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)
            
            overlay = Image.new("RGBA", size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            for x in range(width):
                alpha = int(215 - (135 * (x / width)))
                overlay_draw.line([(x, 0), (x, height)], fill=(12, 16, 26, alpha))
                
            image = Image.alpha_composite(image, overlay)
            draw = ImageDraw.Draw(image)
        else:
            image = Image.new("RGBA", size)
            draw = ImageDraw.Draw(image)
            color_start = (20, 24, 33)
            color_end = (41, 55, 91)
            for y in range(height):
                ratio = y / height
                r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
                g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
                b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        card_margin = 25
        draw.rounded_rectangle(
            [card_margin, card_margin, width - card_margin, height - card_margin],
            radius=20,
            fill=(255, 255, 255, 5),
            outline=(255, 255, 255, 20),
            width=2
        )

        font_large = self._load_font(32)
        font_medium = self._load_font(20)
        font_small = self._load_font(12)

        # recommended badge
        badge_x1, badge_y1 = 60, 60
        badge_x2, badge_y2 = 195, 88
        draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2], radius=6, fill="#0099FF")
        draw.text((badge_x1 + 16, badge_y1 + 4), "RECOMMENDED", fill=(255, 255, 255, 255), font=font_small)

        # title
        title_x, title_y = 60, 115
        max_title_width = 460
        self._draw_wrapped_text(draw, clean_title, (title_x, title_y), font_large, max_title_width, (255, 255, 255, 255))

        # subtitle
        sub_text = "Latest Hot Selling E-Book & Novel Reviews"
        draw.text((60, 265), sub_text, fill=(210, 215, 225, 200), font=font_medium)

        # Kobo button
        btn_x1, btn_y1 = 60, 325
        btn_x2, btn_y2 = 325, 375
        draw.rounded_rectangle([btn_x1, btn_y1, btn_x2, btn_y2], radius=25, fill="#0099FF")
        draw.text((btn_x1 + 22, btn_y1 + 13), "楽天Koboで詳細を見る ➔", fill=(255, 255, 255, 255), font=font_medium)

        rgb_image = image.convert("RGB")
        rgb_image.save(output_path, "PNG")
        print(f"Eyecatch saved successfully to: {output_path}")
        return output_path
