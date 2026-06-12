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

    def generate_review_article(self, item: Dict[str, Any]) -> str:
        title = item.get("title", "")
        clean_title = item.get("clean_title", title)
        features = "\n".join([f"- {f}" for f in item.get("features", [])])
        price = item.get("price", "")
        url = item.get("url", "")

        prompt = f"""以下のAmazonの商品情報を元に、はてなブログの「編集部おすすめ」に選出されるレベルの、熱量が高く独自の視点に満ちた個人ブログのレビュー記事を執筆してください。
単なる仕様説明や一般的な評価の羅列（テンプレ記事）を徹底的に排除し、あなたの「偏愛」や「ストーリー」を感じさせる、唯一無二の記事に仕上げてください。

【商品名】: {title}
【価格】: {price}
【主な特徴】:
{features}
【商品検索URL】: {url}

【執筆の構成ルール（見出しの自律設計）】:
- 固定された章構成（「はじめに」「デザイン」など）は使用しないでください。商品の特性やあなたが最も伝えたい魅力に合わせ、読者を惹きつけるキャッチーな見出し（3〜5個程度）を自律的に考案してください（例: 「## ◯◯という沼にハマる」「## 1ヶ月使い倒して気づいた、意外な盲点」など）。
- 記事の導入は、製品の無味乾燥な紹介ではなく、あなたの日常の課題や、その製品を導入せざるを得なかった背景などの「ストーリー（エッセイ風の書き出し）」から始めてください。
- 「独自のこだわり評価軸」を必ず1つ設定して語ってください（例: 「ノイキャン性能がもたらす『カフェでの究極の没入感』」「カバンの中の極小スペースにいかに美しく収まるか」など）。
- デメリットや「ここは惜しい！」というポイントを、スペック批判ではなく、実体験に基づくリアルな本音として包み隠さず書いてください。

【執筆の厳格なルール（最優先）】:
1. ブログ記事の**本文のみ**を出力してください。挨拶文（「承知しました」「以下が記事です」など）や、記事の解説、まとめのアドバイス（「以上のように、自然な言葉遣い〜」「購入につなげることができます」など）は**絶対に1文字も出力しないでください**。記事の最後は「ぜひチェックしてみてください！」などの読者へのメッセージで終了させてください。
2. 「アフィリエイト」「アフィリンク」「誘導」「広告」といった、読者に商業的な意図を直接感じさせる言葉は**見出し・本文含め、絶対に記事内に出力しないでください**。
3. 記事はMarkdown（マークダウン）形式で執筆してください。見出しは「## 」「### 」を使用し、箇条書きは「- 」を使用してください。
4. 商品リンクは, 文末付近に自然な形で `[Amazonで「{clean_title}」の価格やクチコミをチェックする]({url})` のようにMarkdownのリンク記法で埋め込んでください。
5. AI特有の「〜はいかがでしょうか」「〜をご紹介します」「〜と言えるでしょう」「〜の特徴を持っています」といった説明調のテンプレフレーズを多用せず、人間が強いこだわりを持って書いたレビューのリアリティと熱量のある文体で書いてください。
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

[Amazonで「{clean_title}」の価格やクチコミをチェックする]({url})
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
                    "text": "あなたはモノに並々ならぬこだわりを持つ個人ブロガーです。商品のスペック説明は最小限にし、この商品を導入したことで日常がどう劇的に変わったかというライフスタイルへの変化（ベネフィット）を、熱量と独自の視点で語ってください。他人事の解説調ではなく、書き手の顔が見える一人称の熱い語り口で執筆してください。指示された厳格なルールと章構成を完全に守り、余計な挨拶や解説を一切含まないブログ本文のみを出力します。\n\n" + prompt
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
                {"role": "system", "content": "あなたはモノに並々ならぬこだわりを持つ個人ブロガーです。商品のスペック説明は最小限にし、この商品を導入したことで日常がどう劇的に変わったかというライフスタイルへの変化（ベネフィット）を、熱量と独自の視点で語ってください。他人事の解説調ではなく、書き手の顔が見える一人称の熱い語り口で執筆してください。指示されたルールを厳格に守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
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
                {"role": "system", "content": "あなたはモノに並々ならぬこだわりを持つ個人ブロガーです。商品のスペック説明は最小限にし、この商品を導入したことで日常がどう劇的に変わったかというライフスタイルへの変化（ベネフィット）を、熱量と独自の視点で語ってください。他人事の解説調ではなく、書き手の顔が見える一人称の熱い語り口で執筆してください。指示された厳格なルールを守り、余計な解説を一切含まない日本語ブログ本文のみを出力します。"},
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
            "inputs": f"<|im_start|>system\nあなたはモノに並々ならぬこだわりを持つ個人ブロガーです。商品のスペック説明は最小限にし、この商品を導入したことで日常がどう劇的に変わったかというライフスタイルへの変化（ベネフィット）を、熱量と独自の視点で語ってください。他人事の解説調ではなく、書き手の顔が見える一人称の熱い語り口で執筆してください。日本語で余計な前置きや後書きなしに、本文のみを出力します。<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
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
                    {"role": "system", "content": "あなたはモノに並々ならぬこだわりを持つ個人ブロガーです。商品のスペック説明は最小限にし、この商品を導入したことで日常がどう劇的に変わったかというライフスタイルへの変化（ベネフィット）を、熱量と独自の視点で語ってください。他人事の解説調ではなく、書き手の顔が見える一人称の熱い語り口で執筆してください。指示されたルールを厳格に守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
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
