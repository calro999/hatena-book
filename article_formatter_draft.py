import os
import re
import json
import requests
from typing import Dict, Any, Tuple, Optional

class DraftArticleFormatter:
    """ユーザー指定の高品質スタイルに完全準拠したHTMLレビュー記事ジェネレーター"""

    # Gemini 1.5系は完全廃止のため絶対禁止。最新世代のみローテーション
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

        # responseMimeType: "application/json" で厳密なJSON出力を強制
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json"
            }
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
                else:
                    print(f"Gemini {model_name} HTTP {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                print(f"Gemini {model_name} error: {e}")
        return None

    def _parse_llm_json(self, raw_text: str) -> Dict[str, str]:
        """強固なJSONパーサー（改行や未エスケープ文字があってもキー単位で高精度抽出）"""
        clean = raw_text.strip()
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean, re.DOTALL)
        candidate = match.group(1) if match else clean
        s = candidate.find('{')
        e = candidate.rfind('}')
        if s != -1 and e != -1:
            candidate = candidate[s:e+1]

        # 1. 直接のjson.loadsを試行
        try:
            return json.loads(candidate)
        except Exception:
            pass

        # 2. 失敗時は正規表現でキー単位に抽出（途切れや未エスケープ改行を救済）
        data = {}
        keys = [
            "title", "hook_p1", "hook_p2", "hook_p3", "cta_text_1",
            "sec1_h2", "sec1_p1", "sec1_p2", "sec1_p3", "cta_text_2",
            "sec2_h3", "sec2_p1", "sec2_p2", "summary_lead", "summary_body", "cta_text_3"
        ]
        for key in keys:
            pattern = r'"' + key + r'"\s*:\s*"([^"\]*(?:\.[^"\]*)*)"'
            m = re.search(pattern, raw_text, re.DOTALL)
            if m:
                val = m.group(1)
                val = val.replace('\\"', '"').replace("\\n", " ").strip()
                data[key] = val.strip()
        return data

    def generate_article(self, item: Dict[str, Any], placeholder_affiliate_url: str = "") -> Tuple[str, str]:
        """各商品ごとに完全に独立した文章・タイトルを生成（使い回し・定型接頭辞は完全禁止）"""
        name = item.get("name", "")
        clean_name = item.get("clean_name", name)
        price = item.get("price", "")
        desc = item.get("description", "")
        seller = item.get("seller", "")
        
        url = placeholder_affiliate_url or item.get("url", "")
        
        images = item.get("images", [])
        img1 = images[0] if len(images) > 0 else f"https://item-shopping.c.yimg.jp/i/l/{item.get('image_id')}"
        img2 = images[1] if len(images) > 1 else img1
        img3 = images[2] if len(images) > 2 else img1

        prompt = f"""あなたは一流のプロWebコピーライター・商品レビュー専門家です。
以下のYahoo!ショッピング商品情報に基づき、読者を強く惹きつける完全オリジナルで独立したレビュー記事を作成してください。

【厳格禁止事項（絶対遵守）】
1. 他の記事と同じ文章、テンプレート構文、定型表現の使い回しは【一切禁止】。
2. タイトルに「【話題沸騰】」「【本音レビュー】」「【徹底検証】」「まとめ」「速報」などの定型接頭辞を付けることは【絶対禁止】（スパム判定されるため）。
3. タイトルは絶対に途中で途切れさせず、意味の通る美しい日本語で完結させること（30〜35文字程度）。
4. HTMLのコメント（<!-- ... -->）は一切出力に含めないこと。
5. AI臭いありきたりな表現（「いかがでしたでしょうか」「〜してみてはいかがでしょうか」「魅力をご紹介します」等）は排除し、読者に寄り添う自然で熱量のある文章にすること。

【商品情報】
商品名: {name}
通称: {clean_name}
価格: {price}
ショップ: {seller}
商品説明: {desc}

【出力フォーマット】
以下のキーを持つJSONオブジェクトのみを出力してください（Markdownの装飾なしで直接JSON文字列のみ出力）：
{{
  "title": "商品固有の特徴・ベネフィットが伝わり、途中で絶対に途切れていない魅力的なタイトル（30〜35文字）",
  "hook_p1": "読者の日常の悩みや現状を突く疑問投げかけ（この商品ならではの具体的なシチュエーション）",
  "hook_p2": "現状を放置することによるデメリットや潜在的な損失・不便さの指摘",
  "hook_p3": "この商品を手に入れた瞬間に得られる感動的な変化や解決策の提示",
  "cta_text_1": "冒頭CTAボタンの文言（商品名を入れた自然な誘導）",
  "sec1_h2": "解説1の見出し（絵文字付き、この商品ならではの画期的な機能や特徴）",
  "sec1_p1": "読者の共感や日常の不満・不便さのリアルな描写（約140字）",
  "sec1_p2": "商品の仕組みやこだわり、特徴の具体的解説（約140字）",
  "sec1_p3": "実際の使い心地と他にはない圧倒的メリット（約140字）",
  "cta_text_2": "中盤CTAボタンの文言（価格や詳細を確認したくなるフレーズ）",
  "sec2_h3": "解説2の見出し（絵文字付き、素材・耐久性・デザインのこだわり）",
  "sec2_p1": "安心感や安全性、品質への配慮（約140字）",
  "sec2_p2": "生活のなかで長く愛用できる理由やスマートな活躍（約140字）",
  "summary_lead": "まとめの問いかけ（妥協をやめて本物を手に入れる決断を促す1文）",
  "summary_body": "読者の背中をそっと押す、心強い推薦・応援メッセージ（約120字）",
  "cta_text_3": "最後のCTAボタンの文言（公式商品ページへの後押し）"
}}"""

        ai_response = self._call_gemini(prompt)
        parsed = self._parse_llm_json(ai_response) if ai_response else {}

        # タイトルの取得（絶対に途切れさせず、定型接頭辞は完全排除）
        title = parsed.get("title", "").strip()
        # 定型タグの除去
        title = re.sub(r'^(【.*?】|\[.*?\])\s*', '', title).strip()
        if not title:
            # フォールバック時も定型語「話題沸騰」を完全排除し、商品固有のタイトルを動的生成
            title = f"{clean_name}の魅力と使い心地を徹底レビュー"

        hook_p1 = parsed.get("hook_p1") or f"日々の生活の中で、『{clean_name}』の快適さや使い勝手が気になっていませんか？"
        hook_p2 = parsed.get("hook_p2") or "我慢や妥協を続けていると、日々の小さなストレスや時間のロスが積み重なってしまいます。"
        hook_p3 = parsed.get("hook_p3") or f"そんな悩みをスマートに解消してくれる『{clean_name}』なら、手にしたその日からワンランク上の心地よさを実感できます。"
        cta_text_1 = parsed.get("cta_text_1") or f"『{clean_name}』の公式商品ページを見る"

        sec1_h2 = parsed.get("sec1_h2") or f"✨ 日常の快適さを底上げする『{clean_name}』のこだわり"
        sec1_p1 = parsed.get("sec1_p1") or "毎日使うものだからこそ、ちょっとした使いづらさが蓄積すると大きなストレスになります。"
        sec1_p2 = parsed.get("sec1_p2") or f"この『{clean_name}』は、使う人のリアルなニーズを丁寧に汲み取って設計されており、確かな違いを感じられます。"
        sec1_p3 = parsed.get("sec1_p3") or "手に取った瞬間にわかる丁寧な仕上がりと実用性の高さは、日々の生活を確実に豊かにしてくれます。"
        cta_text_2 = parsed.get("cta_text_2") or "最新の価格・バリエーションを確認する"

        sec2_h3 = parsed.get("sec2_h3") or "🌿 毎日心地よく使える安心設計と高い耐久性"
        sec2_p1 = parsed.get("sec2_p1") or "使い勝手はもちろん、長く愛用できるよう素材や細部のディテールまで妥協なく仕上げられています。"
        sec2_p2 = parsed.get("sec2_p2") or "暮らしの中に自然と溶け込むスマートな佇まいで、どんなシーンでも頼もしいパートナーとなってくれます。"

        summary_lead = parsed.get("summary_lead") or f"日々の暮らしをより豊かに変える『{clean_name}』"
        summary_body = parsed.get("summary_body") or "毎日のモチベーションを高めてくれる心強いアイテム。気になっている方は、ぜひ在庫のあるうちにチェックしてみてください。"
        cta_text_3 = parsed.get("cta_text_3") or "在庫状況と詳細をチェックする"

        # 確実に実在するYahoo画像【3枚のみ】を配置（HTMLコメントは完全排除）
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
