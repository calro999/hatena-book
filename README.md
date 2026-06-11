# hatena-kobo-bot

楽天Kobo電子書籍検索APIから最新の新刊情報を取得し、複数の無料LLM API（Gemini, GitHub Models, OpenRouter, Hugging Face, Pollinations）の自動フォールバック機能を用いて魅力的な紹介文を生成、さらにはてなブログへ完全自動で投稿するシステムです。

## 特徴
1. **楽天Kobo電子書籍検索API連携**: 常に最新の発売日順で作品データをチェック。
2. **時間帯ローテーション**: 実行する日本時間（JST）の奇数／偶数時間に応じて、コミックジャンルとライトノベルジャンルを自動切り替え。
3. **重複投稿防止（キャッシュ機能）**: 投稿済みの商品コード（`itemNumber`）を `posted_cache.txt` で管理し、重複投稿を完全に防止。
4. **自動アイキャッチ合成**: Unsplashの本・マンガに関連する美しい画像をベースに、Pillowでタイトルやボタン等を合成したバナーを自動生成。
5. **堅牢なLLMフォールバック**: 無料のLLM APIをローテーションで呼び出し、API制限やキー未設定時でも動作を維持。あらすじ以外の創作（ハルシネーション）を防ぐプロンプト設計。
6. **強力なアフィリエイトCTA**: 記事末尾に目立つ「＼ 今すぐ無料で試し読みする ／」ボタン（アフィリエイトリンク）を自動配置。

---

## ディレクトリ構成
- `kobo_blogger.py`: 全体を統括するメインスクリプト
- `article_generator.py`: LLMによるあらすじ解説・おすすめ紹介の生成ロジック
- `image_generator.py`: バナー画像のUnsplash検索およびPillow文字合成ロジック
- `hatena_api.py`: はてなブログ（AtomPub / フォトライフ）連携ロジック
- `.github/workflows/cron.yml`: 毎時0分の自動実行およびキャッシュ自動プッシュを定義するGitHub Actionsワークフロー
- `requirements.txt`: 依存ライブラリ一覧
- `posted_cache.txt`: 投稿済み商品コードキャッシュ（自動生成）

---

## セットアップ手順

### 1. GitHub Secrets の設定
GitHubリポジトリの `Settings` > `Secrets and variables` > `Actions` に以下を登録してください。

| シークレット名 | 説明 |
| :--- | :--- |
| `RAKUTEN_APP_ID` | 楽天ウェブサービス アプリID |
| `RAKUTEN_AFFILIATE_ID` | 楽天アソシエイトID (アフィリエイトID) |
| `HATENA_ID` | はてなID (はてなブログのアカウント名) |
| `HATENA_BLOG_ID` | はてなブログのドメイン（例: `your-blog.hatenablog.com`） |
| `HATENA_API_KEY` | はてなブログ管理画面「詳細設定」から取得できるAPIキー |
| `GEMINI_API_KEY` | Gemini APIキー (任意: LLM生成のファーストチョイスとして使用) |

### 2. ローカルでの動作確認（ドライラン）
APIキーなどを設定せずにローカルで実行すると、自動的に「ドライランモード（ダミーデータ＆モックモデル）」で動作し、ファイルの生成結果をコンソールに出力します。

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テスト実行
python kobo_blogger.py
```
実行完了後、カレントディレクトリに `eyecatch.png` が生成され、はてなブログに投稿される記事本文がコンソールに出力されます。また、`posted_cache.txt` が生成されます。
