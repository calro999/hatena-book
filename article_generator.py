import os
import re
import requests
import json
import time
from typing import Dict, Any, Optional, List

class ArticleGenerator:
    def __init__(self, model_id: str = ""):
        pass

    def load_model(self):
        print("ArticleGenerator: Initialized using online free API router.")
        pass

    def generate_review_article(self, item: Dict[str, Any]) -> str:
        title = item.get("title", "")
        item_caption = item.get("itemCaption", "").strip()
        if not item_caption:
            item_caption = "（公式のあらすじが登録されていません。新刊情報から詳細をご確認ください。）"

        prompt = f"""以下の電子書籍の公式あらすじ（itemCaption）を元に、紹介セクションを作成してください。

【書名】: {title}
【公式あらすじ】:
{item_caption}

【紹介文執筆の厳格なルール】
1. 与えられた「公式あらすじ」に記載されていない情報（結末、裏設定、あらすじにない登場人物、存在しない評判や感想など）は絶対に創作（ハルシネーション）しないでください。あらすじにある事実のみに基づき、魅力的にリライト・紹介してください。
2. 以下の構成ルールに厳格に従い、Markdown形式で出力してください。
3. 挨拶文（「承知しました」「以下が紹介文です」など）や、解説、余計な前置き・後書きは【絶対に1文字も】出力しないでください。

【構成ルール】
### 注目ポイント
- [注目ポイント1をあらすじから魅力的にリライト]
- [注目ポイント2をあらすじから魅力的にリライト]
- [注目ポイント3をあらすじから魅力的にリライト]

### こんな人におすすめ
[あらすじに基づき、どんな人にこの本がおすすめかを2行程度でポジティブに紹介]
"""

        # Trial order of Free LLM APIs (Same as hatena-mono)
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
                if res and len(res.strip()) > 100:
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
                print("WARNING: All free LLM APIs failed or are rate-limited. Since this is a local dry-run, generating dummy review text.")
                raw_article = f"""### 注目ポイント
- 本書公式のあらすじに基づく、独自のストーリー展開と魅力的なキャラクター設定
- 本日発売されたばかりの注目作品の最新刊
- 読者の興味を惹きつける見どころの凝縮

### こんな人におすすめ
新刊情報をいち早くチェックしたい方や、あらすじから新しい読書体験を探しているすべての方におすすめの一冊です。"""

        # Post-Processing to clean up LLM meta-explanations
        raw_article = re.sub(r"^(はい、|承知いたしました。|以下が紹介文です。|以下に記事を出力します。|以下が執筆した記事です。)\s*", "", raw_article)

        # Convert Markdown to HTML for Hatena Blog compatibility
        import markdown
        html_output = markdown.markdown(raw_article, extensions=['nl2br'])
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
                    "text": "あなたはプロの書評ブロガーです。与えられたあらすじ以外の情報を勝手に創作（ハルシネーション）しないことが最も重要です。指示されたルールと章構成を完全に守り、余計な挨拶や解説を一切含まないブログ本文のみを出力します。\n\n" + prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000
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
                {"role": "system", "content": "あなたはプロの書評ブロガーです。与えられたあらすじ以外の情報を勝手に創作（ハルシネーション）しないことが最も重要です。指示されたルールを守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
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
                {"role": "system", "content": "あなたはプロの書評ブロガーです。与えられたあらすじ以外の情報を勝手に創作（ハルシネーション）しないことが最も重要です。指示された厳格なルールを守り、余計な解説を一切含まない日本語ブログ本文のみを出力します。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
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
            "inputs": f"<|im_start|>system\nあなたはプロの書評ブロガーです。与えられたあらすじ以外の情報を勝手に創作（ハルシネーション）しないことが最も重要です。日本語で余計な前置きや後書きなしに、本文のみを出力します。<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
            "parameters": {
                "max_new_tokens": 800,
                "temperature": 0.2
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
        url = "https://text.pollinations.ai/"
        models = ["openai", "qwen", "mistral"]
        
        for attempt, model in enumerate(models):
            payload = {
                "messages": [
                    {"role": "system", "content": "あなたはプロの書評ブロガーです。与えられたあらすじ以外の情報を勝手に創作（ハルシネーション）しないことが最も重要です。指示されたルールを厳格に守り、日本語で前置き・後書きなしでブログ本文のみを出力してください。"},
                    {"role": "user", "content": prompt}
                ],
                "model": model
            }
            try:
                print(f"Trying Pollinations AI POST (model: {model}, attempt: {attempt+1})...")
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200 and len(resp.text.strip()) > 100:
                    return resp.text
                elif resp.status_code == 429:
                    print(f"Pollinations AI {model} returned 429. Waiting {attempt+2}s...")
                    time.sleep(attempt+2)
                else:
                    print(f"Pollinations AI {model} returned status {resp.status_code}")
            except Exception as e:
                print(f"Pollinations POST attempt for {model} failed: {e}")
            
        return None
