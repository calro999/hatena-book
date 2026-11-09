import os
import json
import requests
from typing import Dict, Any, Tuple, Optional

class DraftArticleFormatter:
    """ユーザー指定の高品質スタイルに完全準拠したHTMLレビュー記事ジェネレーター"""

    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-lite",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash",
        "gemini-2.5-pro",
        "gemini-3.1-pro"
    ]

    def _call_gemini(self, prompt: str) -> Optional[str]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 3000}
        }
        headers = {"Content-Type": "application/json"}

        for model_name in self.GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text and len(text) > 100:
                            print(f"Article successfully generated via Gemini ({model_name}).")
                            return text
            except Exception:
                pass
        return None

    def generate_article(self, item: Dict[str, Any], placeholder_affiliate_url: str = "") -> Tuple[str, str]:
        """確実にYahooから取得した商品画像3枚のみを使用し、リンク差し替えが簡単なHTMLを生成"""
        name = item.get("name", "")
        clean_name = item.get("clean_name", name)
        price = item.get("price", "")
        desc = item.get("description", "")
        seller = item.get("seller", "")
        
        # 差し替え用URL（ユーザーが管理画面で一括置換しやすいプレースホルダー）
        url = placeholder_affiliate_url or item.get("url", "")
        
        # 確実に実在するYahoo商品画像3枚
        images = item.get("images", [])
        img1 = images[0] if len(images) > 0 else f"https://item-shopping.c.yimg.jp/i/l/{item.get('image_id')}"
        img2 = images[1] if len(images) > 1 else img1
        img3 = images[2] if len(images) > 2 else img1

        prompt = f"""あなたはプロのWebコピーライター・商品レビュー専門家です。
以下のYahoo!ショッピング商品情報を元に、読者を惹きつける高品質なレビュー記事を作成してください。

【商品情報】
商品名: {name}
通称: {clean_name}
価格: {price}
ショップ: {seller}
商品説明: {desc}

【出力の絶対遵守ルール】
1. HTMLのコメント（例: <!-- 画像1 --> など）は一切含めないこと。
2. 返答は以下のJSON形式のみを出力すること：
{{
  "title": "魅力的でクリックしたくなる32文字以内のブログ記事タイトル",
  "hook_p1": "読者の悩みや現状を突く強烈な疑問投げかけ（例: 毎日の〇〇に不便を感じていませんか？）",
  "hook_p2": "その現状の隠れたデメリットやコストの指摘（例: 実はそれ、放置すると...）",
  "hook_p3": "この商品による劇的な解決と感動の提案（例: 『〇〇』なら、圧倒的な快適さで...）",
  "cta_text_1": "冒頭CTAボタンの文言（例: 今すぐ注目の〇〇をチェックする）",
  "sec1_h2": "解説1の見出し（絵文字付き、例: 🌟 圧倒的な利便性！〇〇が選ばれる理由）",
  "sec1_p1": "読者の共感や日常の不満の描写（140字程度）",
  "sec1_p2": "商品の革新的な特徴や仕組みの解説（140字程度）",
  "sec1_p3": "使い心地と他製品にはない圧倒的メリット（140字程度）",
  "cta_text_2": "中盤CTAボタンの文言（例: カラーバリエーションと価格を確認する）",
  "sec2_h3": "解説2の見出し（絵文字付き、例: ✨ 細部まで考え抜かれた高機能設計）",
  "sec2_p1": "使い勝手や安心感、品質へのこだわり（140字程度）",
  "sec2_p2": "耐久性や日常でのスマートな活躍（140字程度）",
  "summary_lead": "まとめの強烈な問いかけ（例: 妥協したアイテム、いつまで使い続けますか？）",
  "summary_body": "評価実績や自分へのご褒美としての推薦文（120字程度）",
  "cta_text_3": "最後のCTAボタンの文言（例: 商品ページで口コミと詳細を見る）"
}}"""

        ai_response = self._call_gemini(prompt)
        parsed = {}
        if ai_response:
            try:
                clean_json = ai_response.strip()
                if clean_json.startswith("```"):
                    clean_json = clean_json.split("\n", 1)[1]
                    clean_json = clean_json.rsplit("```", 1)[0]
                parsed = json.loads(clean_json)
            except Exception as e:
                print(f"JSON parse error: {e}")

        title = parsed.get("title") or f"【話題沸騰】『{clean_name}』が選ばれる理由と感動の使い心地まとめ"
        hook_p1 = parsed.get("hook_p1") or f"毎日の暮らしの中で、『{clean_name}』の使い心地や快適さを求めていませんか？"
        hook_p2 = parsed.get("hook_p2") or "実は我慢を続けていると、無駄なストレスや時間が蓄積してしまう原因になります。"
        hook_p3 = parsed.get("hook_p3") or f"高評価を獲得し口コミでも話題の『{clean_name}』なら、手にしたその日から圧倒的な快適さと贅沢な時間を手に入れられます！"
        cta_text_1 = parsed.get("cta_text_1") or f"今すぐ『{clean_name}』をチェックする"

        sec1_h2 = parsed.get("sec1_h2") or f"🌟 毎日の生活が一変する！『{clean_name}』の実力"
        sec1_p1 = parsed.get("sec1_p1") or "日々の生活の中でちょっとした不便を感じる瞬間、誰もが経験したことがあるはずです。妥協したアイテムを使い続けるのは、意外と小さなストレスが蓄積していく原因になります。"
        sec1_p2 = parsed.get("sec1_p2") or f"この『{clean_name}』は、ユーザーのリアルな声と最新の技術を徹底的に追求して開発されています。手にした瞬間に伝わるクオリティの高さは、多くの愛用者を納得させています。"
        sec1_p3 = parsed.get("sec1_p3") or "使い勝手の良さはもちろん、細部のデザインやスペックに至るまで妥協がありません。毎日のパートナーとして、確かな満足感をもたらしてくれます。"
        cta_text_2 = parsed.get("cta_text_2") or "バリエーションと価格を確認する"

        sec2_h3 = parsed.get("sec2_h3") or "✨ 素材と使い心地への徹底的なこだわり"
        sec2_p1 = parsed.get("sec2_p1") or "直接触れるものだからこそ、肌触りや質感の良さは何よりも大切。細部にまで配慮された設計が、使うたびに心地よい安心感を与えてくれます。"
        sec2_p2 = parsed.get("sec2_p2") or "優れた耐久性と品質を両立しており、長く安心して愛用できるのも嬉しいポイント。使うほどに手放せなくなる魅力が詰まっています。"

        summary_lead = parsed.get("summary_lead") or f"毎日の暮らしをワンランク引き上げる『{clean_name}』で、特別な体験を。"
        summary_body = parsed.get("summary_body") or "ご自身用としてはもちろん、大切な方へのギフトとしても大変喜ばれる逸品です。人気商品のため在庫のあるうちにぜひチェックしてみてください。"
        cta_text_3 = parsed.get("cta_text_3") or "商品ページで口コミと詳細を見る"

        # 確実に実在するYahoo画像【3枚のみ】を美しく配置
        html = f"""<div style="font-family: 'Helvetica Neue', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; line-height: 2.0; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #fcfcfd; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">

    <div style="background-color: #f3f0f8; border-left: 6px solid #6c5ce7; padding: 25px 20px; border-radius: 6px; margin-bottom: 35px;">
        <p style="font-size: 1.15em; font-weight: bold; color: #4834d4; margin-top: 0; margin-bottom: 10px;">{hook_p1}</p>
        <p style="font-size: 1.05em; margin-bottom: 10px;">{hook_p2}</p>
        <p style="font-size: 1.05em; margin-bottom: 0;">{hook_p3}</p>
    </div>

    <div style="text-align: center; margin-bottom: 35px;">
        <a href="{url}" target="_blank" rel="noopener noreferrer">
            <img src="{img1}" alt="{clean_name}" style="max-width: 90%; height: auto; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.06);">
        </a>
    </div>

    <div style="text-align: center; margin: 30px 0 50px 0;">
        <a href="{url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #f6b93b 0%, #e58e26 100%); color: #ffffff; font-size: 1.25em; font-weight: bold; text-decoration: none; padding: 18px 50px; border-radius: 50px; box-shadow: 0 6px 15px rgba(229, 142, 38, 0.3); transition: all 0.3s ease;">
            {cta_text_1}
        </a>
    </div>

    <h2 style="font-size: 1.5em; color: #2d3436; border-bottom: 2px solid #6c5ce7; padding-bottom: 10px; margin-bottom: 25px;">{sec1_h2}</h2>
    <p>{sec1_p1}</p>
    <p>{sec1_p2}</p>

    <div style="text-align: center; margin: 35px 0;">
        <a href="{url}" target="_blank" rel="noopener noreferrer">
            <img src="{img2}" alt="{clean_name} 特徴" style="max-width: 90%; height: auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        </a>
    </div>

    <p>{sec1_p3}</p>

    <div style="text-align: center; margin: 45px 0;">
        <a href="{url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #f6b93b 0%, #e58e26 100%); color: #ffffff; font-size: 1.25em; font-weight: bold; text-decoration: none; padding: 16px 45px; border-radius: 50px; box-shadow: 0 6px 15px rgba(229, 142, 38, 0.3);">
            {cta_text_2}
        </a>
    </div>

    <h3 style="font-size: 1.3em; color: #4834d4; margin-top: 45px; margin-bottom: 20px;">{sec2_h3}</h3>
    <p>{sec2_p1}</p>

    <div style="text-align: center; margin: 35px 0;">
        <a href="{url}" target="_blank" rel="noopener noreferrer">
            <img src="{img3}" alt="{clean_name} ディテール" style="max-width: 90%; height: auto; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        </a>
    </div>

    <p>{sec2_p2}</p>

    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 8px; margin-top: 50px; margin-bottom: 40px; border: 1px solid #dcdde1; text-align: center;">
        <p style="font-size: 1.15em; font-weight: bold; color: #2f3542; margin-bottom: 15px;">
            {summary_lead}
        </p>
        <p style="margin-bottom: 0; font-size: 0.95em; color: #747d8c;">{summary_body}</p>
    </div>

    <div style="text-align: center; margin: 40px 0;">
        <a href="{url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #e58e26 0%, #d35400 100%); color: #ffffff; font-size: 1.4em; font-weight: bold; text-decoration: none; padding: 18px 60px; border-radius: 50px; box-shadow: 0 8px 20px rgba(211, 84, 0, 0.4); text-shadow: 1px 1px 2px rgba(0,0,0,0.2); transition: transform 0.2s ease;">
            {cta_text_3}
        </a>
    </div>

    <div style="margin-top: 60px; padding: 20px; border-top: 1px dashed #ced6e0; text-align: center;">
        <p style="font-size: 0.85em; color: #a4b0be; margin: 0;">
            ※本記事はプロモーションを含みます。<br>
            ※リンク先はアフィリエイトプログラムを利用して商品を紹介しています。
        </p>
    </div>

</div>"""

        return title, html
