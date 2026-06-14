import os
import re
import requests
import json
import time
import urllib.parse
from typing import Dict, Any, Optional, List

class ArticleGenerator:
    def __init__(self, model_id: str = ""):
        pass

    def load_model(self):
        print("ArticleGenerator: Initialized using online free API router (No local models loaded).")
        pass

    def translate_synopsis(self, text: str) -> str:
        """Translates the given synopsis to natural Japanese if it is in English or needs formatting."""
        if not text:
            return ""
            
        # Check if the text contains mostly English/non-Japanese characters
        # If it's already in Japanese, we might still want to clean/format it, but we definitely want to translate if it is English.
        prompt = f"""以下の文章（書籍のあらすじ・紹介文）を、魅力的で自然な日本語に翻訳および整形してください。
もし元の文章が英語の場合は、日本語の丁寧な文章に翻訳してください。
既に日本語の場合は、より読みやすく魅力的なあらすじに整えてください。

【元の文章】:
{text}

【出力ルール（厳格）】:
- 翻訳・整形後の日本語のあらすじ本文のみを出力してください。
- 挨拶や余計な解説（「以下が翻訳です」など）は絶対に含めないでください。
"""

        generators = [
            ("Gemini API (Free Tier)", self._generate_with_gemini),
            ("GitHub Models API (Free for Actions/PAT)", self._generate_with_github_models),
            ("OpenRouter Free API", self._generate_with_openrouter),
            ("Hugging Face API (Free Tier)", self._generate_with_huggingface),
            ("Pollinations AI Free (No Key Required)", self._generate_with_pollinations),
        ]

        translated_text = None
        for name, gen_fn in generators:
            try:
                print(f"Attempting synopsis translation with {name}...")
                res = gen_fn(prompt)
                if res and len(res.strip()) > 10:
                    translated_text = res.strip()
                    print(f"Successfully translated synopsis using {name}!")
                    break
            except Exception as e:
                print(f"Error calling {name} for translation: {e}. Trying next fallback...")

        if not translated_text:
            print("WARNING: All translation APIs failed. Using original text.")
            return text

        # Clean up any potential markdown formatting or prefix/suffix that LLMs sometimes generate
        translated_text = re.sub(r"^(はい、|承知いたしました。|以下が翻訳です。|以下に日本語訳を出力します。|翻訳結果：|翻訳：)\s*", "", translated_text)
        return translated_text

    def generate_review_article(self, item: Dict[str, Any]) -> str:
        title = item.get("title", "")
        clean_title = item.get("clean_title", title)
        features = "\n".join([f"- {f}" for f in item.get("features", [])])
        price = item.get("price", "")
        url = item.get("url", "")

        prompt = f"""以下の楽天Kobo電子書籍の商品情報を元に、電子書籍紹介サイト「電子書籍チェッカー」の記事として、読者が作品を読みたくなるような魅力的で客観的な作品紹介記事を執筆してください。
単なる公式あらすじのコピーではなく、作品の見どころや魅力を分かりやすく整理した、価値のある書評・紹介記事に仕上げてください。

【作品名】: {title}
【ジャンル】: {price}
【主な特徴/概要】:
{features}
【商品URL】: {url}

【執筆の構成ルール（見出しの自律設計）】:
- 作品の魅力を読者にアピールする、キャッチーな見出し（3〜4個程度）を考案してください（例: 「## 圧倒的な設定と魅力的な世界観」「## 物語を彩る魅力的なキャラクターたち」など）。
- 導入文では、作品の基本情報や「なぜ今注目されているのか」を客観的かつ魅力的に紹介してください。
- 最後に、どのような読者（例: 「異世界スローライフが好きな人」「胸キュン恋愛ものが読みたい人」など）におすすめかを整理してまとめてください。

【執筆の厳格なルール（最優先）】:
1. ブログ記事の**本文のみ**を出力してください。挨拶文（「承知しました」「以下が記事です」など）や、記事の解説などは**絶対に1文字も出力しないでください**。記事の最後は「ぜひチェックしてみてください！」などの読者へのメッセージで終了させてください。
2. 一人称（「私」「俺」「僕」など）は使用せず、客観的な三人称・編集部としての視点で執筆してください。執筆者自身のプライベートなエピソードや日記風の内容（「最近仕事が忙しかった」など）は絶対に含めないでください。
3. 記事はMarkdown（マークダウン）形式で執筆してください。見出しは「## 」「### 」を使用し、箇条書きは「- 」を使用してください。
4. 商品リンクは、文末付近に自然な形で `[楽天Koboで「{clean_title}」の電子書籍をチェックする]({url})` のようにMarkdown의 リンク記法で埋め込んでください。
5. AI特有の過度なテンプレ調の言葉遣いを避けつつ、書評メディアのライターとしての信頼感と熱量がある丁寧な敬体（です・ます調）で書いてください。
"""

        # Trial order of Free LLM APIs
        generators = [
            ("Gemini API (Free Tier)", self._generate_with_gemini),
            ("GitHub Models API (Free for Actions/PAT)", self._generate_with_github_models),
            ("OpenRouter Free API", self._generate_with_openrouter),
            ("Hugging Face API (Free Tier)", self._generate_with_huggingface),
            ("Pollinations AI Free (No Key Required)", self._generate_with_pollinations),
        ]

        raw_article = None
        for name, gen_fn in generators:
            try:
                print(f"Attempting article generation with {name}...")
                res = gen_fn(prompt)
                if res and len(res.strip()) > 300:
                    raw_article = res.strip()
                    print(f"Successfully generated article using {name}!")
                    break
                else:
                    print(f"{name} returned empty or too short response. Trying next fallback...")
            except Exception as e:
                print(f"Error calling {name}: {e}. Trying next fallback...")

        # If all LLM APIs failed
        if not raw_article:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise RuntimeError("All free LLM APIs failed to generate a valid review article in GitHub Actions. Cannot proceed to prevent posting spam templates.")
            else:
                print("WARNING: All free LLM APIs failed or are rate-limited. Since this is a local dry-run, generating dummy review text to verify downstream components.")
                raw_article = f"""## ◯◯という沼にハマる
これはローカル開発環境でのドライラン検証用のテスト記事です。現在、すべてのオンライン無料LLM APIがレート制限またはキー未設定のため利用できませんでした。

## 1ヶ月使い倒して気づいた、意外な盲点
この製品は優れたデザインとコンパクトさを兼ね備えています。

## 実用性を超えたマニアックな視点での評価
テスト特徴1、特徴2、特徴3により、非常に高いレベルの実用性を誇ります。

[楽天Koboで「{clean_title}」の電子書籍をチェックする]({url})
ぜひチェックしてみてください！"""

        # Post-Processing to clean up LLM meta-explanations
        raw_article = re.sub(r"^(はい、|承知いたしました。|以下が商品紹介記事です。|以下に記事を出力します。|以下が執筆した記事です。)\s*", "", raw_article)
        meta_markers = [
            "以上のように",
            "このように、",
            "自然な言葉遣いと",
            "アフィリエイトリンクへの",
            "読者は商品の魅力を理解し",
            "購入につなげることができます"
        ]
        for marker in meta_markers:
            if marker in raw_article:
                print(f"Truncating AI meta-explanation found at marker: '{marker}'")
                raw_article = raw_article.split(marker)[0].rstrip()

        # Convert Markdown to HTML for Hatena Blog compatibility
        import markdown
        html_output = markdown.markdown(raw_article, extensions=['nl2br'])
        
        # Force all <a> tags to open in a new tab (target="_blank" rel="noopener noreferrer")
        def add_target_blank(match):
            tag = match.group(0)
            if 'target=' not in tag:
                tag = tag.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ')
            return tag
            
        html_output = re.sub(r'<a\s+[^>]*>', add_target_blank, html_output)
        return html_output

    def _generate_with_gemini(self, prompt: str) -> Optional[str]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": "あなたは電子書籍紹介サイト「電子書籍チェッカー」のプロ書評ライターです。客観的な視点から、作品の見どころや魅力を整理し、読者が読みたくなるような書評・紹介記事を執筆してください。一人称や個人的な日記風のエピソードは一切排除し、丁寧な敬体（です・ます調）で執筆してください。指示されたルールを完全に守り、余計な挨拶や解説を一切含まないブログ本文のみを出力します。\n\n" + prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except KeyError:
                return None
        else:
            print(f"Gemini API returned status {resp.status_code}: {resp.text}")
        return None

    def _generate_with_github_models(self, prompt: str) -> Optional[str]:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            return None
        
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "あなたは電子書籍紹介サイト「電子書籍チェッカー」のプロ書評ライターです。客観的な視点から、作品の見どころや魅力を整理し、読者が読みたくなるような書評・紹介記事を執筆してください。一人称や個人的な日記風のエピソードは一切排除し、丁寧な敬体（です・ます調）で執筆してください。指示されたルールを完全に守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            try:
                return resp.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                return None
        else:
            print(f"GitHub Models API returned status {resp.status_code}: {resp.text}")
        return None

    def _generate_with_openrouter(self, prompt: str) -> Optional[str]:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return None
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "google/gemma-2-9b-it:free",
            "messages": [
                {"role": "system", "content": "あなたは電子書籍紹介サイト「電子書籍チェッカー」のプロ書評ライターです。客観的な視点から、作品の見どころや魅力を整理し、読者が読みたくなるような書評・紹介記事を執筆してください。一人称や個人的な日記風のエピソードは一切排除し、丁寧な敬体（です・ます調）で執筆してください。指示されたルールを完全に守り、余計な解説を一切含まない日本語ブログ本文のみを出力します。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except KeyError:
                return None
        else:
            print(f"OpenRouter API returned status {resp.status_code}: {resp.text}")
        return None

    def _generate_with_huggingface(self, prompt: str) -> Optional[str]:
        api_key = os.environ.get("HF_API_KEY") or os.environ.get("HF_TOKEN")
        if not api_key:
            return None
        
        model_id = "Qwen/Qwen2.5-72B-Instruct"
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": f"<|im_start|>system\nあなたは電子書籍紹介サイト「電子書籍チェッカー」のプロ書評ライターです。客観的な視点から、作品の見どころや魅力を整理し、読者が読みたくなるような書評・紹介記事を執筆してください。一人称や個人的な日記風のエピソードは一切排除し、丁寧な敬体（です・ます調）で執筆してください。日本語で余計な前置きや後書きなしに、本文のみを出力します。<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
            "parameters": {
                "max_new_tokens": 1500,
                "temperature": 0.7
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            try:
                text = data[0]["generated_text"]
                if "assistant\n" in text:
                    return text.split("assistant\n")[-1]
                return text
            except (KeyError, IndexError):
                return None
        else:
            print(f"Hugging Face API returned status {resp.status_code}: {resp.text}")
        return None

    def _generate_with_pollinations(self, prompt: str) -> Optional[str]:
        """Pollinations AIのテキスト生成。異なるモデルでPOSTリトライして429を回避します。"""
        url = "https://text.pollinations.ai/"
        
        # Try different free models on Pollinations to spread load and avoid 429
        models = ["openai", "qwen", "mistral"]
        
        for attempt, model in enumerate(models):
            payload = {
                "messages": [
                    {"role": "system", "content": "あなたは電子書籍紹介サイト「電子書籍チェッカー」のプロ書評ライターです。客観的な視点から、作品の見どころや魅力を整理し、読者が読みたくなるような書評・紹介記事を執筆してください。一人称や個人的な日記風のエピソードは一切排除し、丁寧な敬体（です・ます調）で執筆してください。指示されたルールを完全に守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
                    {"role": "user", "content": prompt}
                ],
                "model": model
            }
            try:
                print(f"Trying Pollinations AI POST (model: {model}, attempt: {attempt+1})...")
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200 and len(resp.text.strip()) > 300:
                    return resp.text
                elif resp.status_code == 429:
                    print(f"Pollinations AI {model} returned 429. Waiting {attempt+2}s before trying next model...")
                    time.sleep(attempt+2)
                else:
                    print(f"Pollinations AI {model} returned status {resp.status_code}")
            except Exception as e:
                print(f"Pollinations POST attempt for {model} failed: {e}")
            
        return None
