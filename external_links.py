# -*- coding: utf-8 -*-
"""
外部特化メディアおよび相互リンク用サイトへの
親和性スコアリング＆最下部CTAボタン自動生成モジュール
"""
import re
import random
from typing import Dict, Any, Optional

# 1. 優先外部特化メディア（クラカジ / 旅宿クラウド）
PRIORITY_TARGETS = [
    {
        "id": "kurakaji",
        "domain": "kurakaji.vercel.app",
        "url": "https://kurakaji.vercel.app/",
        "site_name": "暮らしを楽にする家電紹介サイト「クラカジ」",
        "button_text": "暮らしを楽にする家電紹介サイト「クラカジ」をチェック ⚡",
        "keywords": [
            "家電", "家具", "ヒーター", "暖房", "こたつ", "加湿器", "電気代", "サーキュレーター", 
            "乾燥", "温風", "電気毛布", "ストーブ", "扇風機", "空気清浄機", "掃除機", "クリーナー", 
            "デスクライト", "ライト", "照明", "チェア", "デスク", "収納", "ラック", "ケトル", 
            "ドライヤー", "シェーバー", "スマート家電", "スマートリモコン", "脱臭機", "温湿度計",
            "インテリア", "テーブル", "ソファー", "ベッド", "マットレス", "ルンバ", "ロボット掃除機",
            "キッチン家電", "調理家電", "冷蔵庫", "洗濯機", "電子レンジ", "オーブン", "炊飯器"
        ],
        "lead_text": "日々の暮らしや家事をグッと快適・スマートに！家具・家電の賢い選び方や最新レビューは「クラカジ」で詳しく紹介されています。",
        "bg_gradient": "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
        "btn_shadow": "rgba(2, 132, 199, 0.35)"
    },
    {
        "id": "croud-travel",
        "domain": "croud-travel.pages.dev",
        "url": "https://croud-travel.pages.dev/",
        "site_name": "素敵な旅をお届け！「旅宿クラウド」",
        "button_text": "素敵な旅をお届け！「旅宿クラウド」で宿・観光を見る ✈️",
        "keywords": [
            "トラベル", "旅行", "出張", "ポーチ", "圧縮", "スーツケース", "ホテル", "温泉", 
            "宿泊", "パッキング", "移動", "キャリー", "キャリーケース", "ネックピロー", "パスポート", 
            "観光", "おでかけ", "ドライブ", "レジャー", "アウトドア", "新幹線", "飛行機", "旅",
            "旅館", "トラベルポーチ", "アイマスク", "耳栓", "海外旅行", "国内旅行", "キャリーバッグ"
        ],
        "lead_text": "お気に入りのアイテムを持って素敵な旅へ出かけませんか？旅先での極上ステイやおすすめ宿・観光情報は「旅宿クラウド」をぜひご覧ください。",
        "bg_gradient": "linear-gradient(135deg, #059669 0%, #047857 100%)",
        "btn_shadow": "rgba(5, 150, 105, 0.35)"
    }
]

# 2. 相互リンク対象の実在運営サイト
RECIPROCAL_TARGETS = [
    {
        "id": "monorepo",
        "domain": "mono-repo.hatenablog.jp",
        "url": "https://mono-repo.hatenablog.jp/",
        "site_name": "アイテムレビューなら「ものレポ！」 | monorepo!",
        "button_text": "「ものレポ！」で注目のアイテムレビューを見る 📦",
        "keywords": [
            "ガジェット", "便利グッズ", "雑貨", "日用品", "ツール", "イヤホン", "マウス", 
            "キーボード", "充電器", "デスク周り", "周辺機器", "生活雑貨", "文房具", "pc", "スマホ"
        ],
        "lead_text": "日々の生活やデスク周りを快適にする注目アイテム・実用ツールの徹底レビューは「ものレポ！」でチェック！",
        "bg_gradient": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "btn_shadow": "rgba(15, 23, 42, 0.35)"
    },
    {
        "id": "kobo-checker",
        "domain": "book-muryo.hateblo.jp",
        "url": "https://book-muryo.hateblo.jp/",
        "site_name": "ラノベ・漫画の無料試し読み＆新作あらすじ速報｜電子書籍チェッカー",
        "button_text": "「電子書籍チェッカー」で話題作・無料試し読みを見る 📖",
        "keywords": [
            "本", "書籍", "漫画", "マンガ", "コミック", "小説", "ラノベ", "ライトノベル", 
            "電子書籍", "試し読み", "読書", "新刊", "全巻"
        ],
        "lead_text": "今すぐ読みたい話題のコミックや注目のライトノベル、無料試し読み情報は「電子書籍チェッカー」をチェック！",
        "bg_gradient": "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)",
        "btn_shadow": "rgba(124, 58, 237, 0.35)"
    },
    {
        "id": "isekai-compas",
        "domain": "isekai-compas.vercel.app",
        "url": "https://isekai-compas.vercel.app/",
        "site_name": "ラノベまとめサイト！異世界コンパス",
        "button_text": "「異世界コンパス」で異世界・ファンタジー作品を見る 🧭",
        "keywords": [
            "異世界", "転生", "なろう", "ファンタジー", "悪役令嬢", "チート", "スローライフ", 
            "追放", "ラノベ", "魔王", "勇者", "冒険", "魔法"
        ],
        "lead_text": "異世界転生・ファンタジー好き必見！おすすめの異世界ラノベや話題の作品まとめは「異世界コンパス」でたっぷり紹介しています。",
        "bg_gradient": "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
        "btn_shadow": "rgba(13, 148, 136, 0.35)"
    },
    {
        "id": "mikke-hobby",
        "domain": "mikke-hobby.hatenablog.com",
        "url": "https://mikke-hobby.hatenablog.com/",
        "site_name": "人気ガチャ＆キャラクターグッズ「みっけホビー」",
        "button_text": "「みっけホビー」で注目カプセルトイ＆グッズを見る 🎁",
        "keywords": [
            "ガチャ", "カプセルトイ", "フィギュア", "ちいかわ", "ぬいぐるみ", "マスコット", 
            "キャラクター", "サンリオ", "キーホルダー", "ホビー", "アニメ", "食玩", "一番くじ"
        ],
        "lead_text": "デスクやお部屋を彩る大人気カプセルトイや限定キャラクターグッズの最新情報は「みっけホビー」をチェック！",
        "bg_gradient": "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
        "btn_shadow": "rgba(234, 88, 12, 0.35)"
    }
]

def find_best_external_link(
    item_title: str, 
    item_caption: str = "", 
    current_site: str = "",
    allow_prob: float = 0.55
) -> Optional[Dict[str, Any]]:
    """
    商材情報から最も親和性の高いリンク先を選定。
    スパム認定防止のため、毎回ではなく確率（デフォルト約55%）および関連性の高い場合のみ表示。

    優先順位:
    1. 家具・家電に近しい場合 -> クラカジ（最優先）
    2. 旅行に絡められそうな場合 -> 旅宿クラウド（最優先）
    3. 共通点のある相互サイト (monorepo, book-muryo, isekai-compas, mikke-hobby 等 / 自サイト以外)
    """
    text = (item_title + " " + item_caption).lower()

    # 1. 最優先チェック: クラカジ (家具・家電) & 旅宿クラウド (旅行)
    # これらは自然な関連がある場合に最優先
    best_priority = None
    max_p_score = 0
    for target in PRIORITY_TARGETS:
        score = sum(1 for kw in target["keywords"] if kw.lower() in text)
        if score > max_p_score:
            max_p_score = score
            best_priority = target

    if best_priority and max_p_score >= 1:
        return best_priority

    # 2. 相互リンク対象サイトの選定
    # 毎記事貼るとSEOでスパム認定されるリスクがあるため、乱数で約55%の頻度に抑制
    if random.random() > allow_prob:
        return None

    best_reciprocal = None
    max_r_score = 0
    for target in RECIPROCAL_TARGETS:
        # 自サイト自身へのリンクは除外
        if current_site and (current_site in target["id"] or current_site in target["domain"]):
            continue
        score = sum(1 for kw in target["keywords"] if kw.lower() in text)
        if score > max_r_score:
            max_r_score = score
            best_reciprocal = target

    if best_reciprocal and max_r_score >= 1:
        return best_reciprocal

    return None

def generate_external_link_html(target: Optional[Dict[str, Any]]) -> str:
    """最下部配置用の美しいCTAボタン付きカードHTMLを生成"""
    if not target:
        return ""

    bg_grad = target.get("bg_gradient", "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)")
    shadow = target.get("btn_shadow", "rgba(2, 132, 199, 0.35)")
    button_text = target.get("button_text", f"{target['site_name']}を見る")
    lead_text = target.get("lead_text", "")
    url = target["url"]
    site_name = target["site_name"]

    return f'''
<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px 22px; margin: 40px 0 20px 0; box-shadow: 0 4px 18px rgba(0,0,0,0.04); text-align: center;">
    <div style="font-size: 13px; font-weight: bold; color: #64748b; letter-spacing: 0.05em; margin-bottom: 8px;">
        ▼ あわせて読みたいおすすめメディア ▼
    </div>
    <div style="font-size: 17px; font-weight: bold; color: #1e293b; margin-bottom: 12px; line-height: 1.4;">
        {site_name}
    </div>
    <p style="margin: 0 auto 18px auto; max-width: 580px; font-size: 14px; color: #475569; line-height: 1.7; text-align: left;">
        {lead_text}
    </p>
    <div style="margin-top: 10px;">
        <a href="{url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: {bg_grad}; color: #ffffff; font-size: 15px; font-weight: bold; text-decoration: none; padding: 14px 28px; border-radius: 30px; box-shadow: 0 6px 16px {shadow}; transition: transform 0.2s ease;">
            {button_text}
        </a>
    </div>
</div>
'''
