import os
import re
import random
import requests
import urllib.request
import ssl
from typing import List, Dict, Any, Optional

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def is_valid_yahoo_image(url: str) -> bool:
    """Yahoo!の画像URLが実際に存在するか（no-imageダミーでないか）を判定"""
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            if r.status != 200:
                return False
            data = r.read()
            # 4997 bytesはYahooのNo-Image共通ダミー画像
            if len(data) == 4997 or len(data) < 5000:
                return False
            return True
    except Exception:
        return False

def clean_yahoo_title(title: str) -> str:
    """Yahoo!ショッピング特有のSEOキーワード詰め込みやPRタグを除去し、スマートで短い商品名に整形"""
    if not title:
        return "注目アイテム"

    cleaned = title
    brackets = [
        r'\{[^}]*\}', r'【[^】]*】', r'\[[^\]]*\]', r'［[^］]*］',
        r'（[^）]*）', r'\([^)]*\)', r'〈[^〉]*〉', r'《[^》]*》',
        r'〔[^〕]*〕'
    ]
    for b in brackets:
        cleaned = re.sub(b, ' ', cleaned)

    cleaned = re.sub(r'[★☆◆◇■□▲▼◎○〇♪!！?？※・]+', ' ', cleaned)

    promo_words = [
        r'送料無料.*', r'あすつく', r'即納', r'ランキング\s*\d*位', r'第?\d+冠',
        r'クーポン(で|\s*利用で)?\d+%?OFF?', r'ポイント\s*\d+倍', r'PayPay\s*\d+倍',
        r'超PayPay祭', r'お買い物マラソン', r'セール', r'限定', r'正規品',
        r'公式', r'メーカー保証', r'ギフト', r'プレゼント', r'お祝い',
        r'202[4-7]年?(最新|新型)?', r'最新(版|型)?', r'新型', r'景品玩具', r'景品',
        r'おもちゃ', r'雑貨', r'配送区分[A-Z0-9]', r'メール便', r'定形外'
    ]
    for pw in promo_words:
        cleaned = re.sub(pw, ' ', cleaned, flags=re.IGNORECASE)

    delimiters = [r'\s*\|\s*', r'\s*｜\s*', r'\s*／\s*', r'\s*/\s*', r'\s*－\s*', r'\s*:\s*', r'\s*：\s*']
    for delim in delimiters:
        parts = re.split(delim, cleaned)
        if parts and len(parts[0].strip()) >= 4:
            cleaned = parts[0]
            break

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    words = cleaned.split()
    if words:
        result = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + (1 if result else 0) <= 26:
                result.append(w)
                cur_len += len(w) + (1 if len(result) > 1 else 0)
            elif not result:
                result.append(w[:24])
                break
            else:
                break
        cleaned = ' '.join(result)

    return cleaned if len(cleaned) >= 3 else title[:22].strip()

class YahooResearcher:
    """Yahoo!ショッピングAPI v3を利用した高精度商品リサーチクライアント"""
    BASE_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

    TARGET_QUERIES = {
        "mono": [
            "ワイヤレスイヤホン ノイズキャンセリング",
            "骨伝導イヤホン Bluetooth",
            "オープンイヤー イヤホン 耳を塞がない",
            "ワイヤレスヘッドホン 密閉型",
            "ノイズキャンセリングヘッドホン 重低音",
            "ゲーミングヘッドセット マイク付き",
            "Bluetooth スピーカー 防水",
            "ポータブルスピーカー 重低音",
            "サウンドバー テレビスピーカー",
            "USB DAC ヘッドホンアンプ",
            "イヤーモニター 有線イヤホン 高音質",
            "ネックスピーカー ワイヤレス 首掛け",
            "FMトランスミッター Bluetooth 高音質",
            "ICレコーダー ボイスレコーダー 小型",
            "ギター エフェクター ディストーション",
            "ギター エフェクター オーバードライブ",
            "ギター エフェクター ディレイ",
            "ギター エフェクター コーラス",
            "ギター エフェクター リバーブ",
            "ベース エフェクター プリアンプ",
            "マルチエフェクター ギター アンプシミュレーター",
            "ワウペダル ギター エフェクター",
            "クリップチューナー ギター ベース",
            "オーディオインターフェイス USB",
            "コンデンサーマイク 配信 USB",
            "ダイナミックマイク ボーカル 配信",
            "MIDIキーボード コントローラー 小型",
            "ミキサー 小型 アナログ USB",
            "エルゴノミクス マウス ワイヤレス",
            "トラックボールマウス Bluetooth",
            "静音マウス ワイヤレス 小型",
            "ゲーミングマウス 超軽量 無線",
            "垂直型マウス エルゴノミクス",
            "メカニカルキーボード 静音 赤軸",
            "メカニカルキーボード 茶軸 ワイヤレス",
            "静電容量無接点方式 キーボード コンパクト",
            "左手デバイス 片手キーボード プログラマブル",
            "テンキー ワイヤレス Bluetooth 薄型",
            "USBハブ Type-C ドッキングステーション 4K",
            "モニターアーム デュアル クランプ式",
            "PCスピーカー 高音質 USB給電",
            "WEBカメラ 4K 広角 マイク内蔵",
            "ペンタブレット 板タブ 小型",
            "液晶ペンタブレット 液タブ 13インチ",
            "キャプチャーボード 4K パススルー Switch PC",
            "外付けSSD ポータブル 高速転送 1TB",
            "ゲームコントローラー ワイヤレス 連射機能",
            "Switch コントローラー 無線 プロコン連射",
            "PC ゲームパッド 背面ボタン ホールエフェクト",
            "アーケードスティック アケコン 格闘ゲーム",
            "ハンコン レーシングホイール ペダル付き",
            "VRゴーグル スマホ用 3Dメガネ",
            "Switch ドック 小型 冷却ファン付き",
            "PS5 充電スタンド コントローラー 急速充電",
            "ゲーミングイヤホン 有線 マイク付き",
            "スマホ ゲームコントローラー 伸縮式",
            "モバイルバッテリー 急速充電 大容量 20000mAh",
            "モバイルバッテリー 小型 軽量 MagSafe",
            "コンセント一体型 モバイルバッテリー 急速充電",
            "GaN 急速充電器 65W Type-C 3ポート",
            "3in1 ワイヤレス充電器 MagSafe スマホスタンド",
            "ポータブル電源 小型 車中泊 キャンプ",
            "ソーラーチャージャー 折りたたみ ソーラーパネル",
            "卓上 電源タップ USB PD 急速充電",
            "マグネット式 充電ケーブル 端子セット",
            "カーチャージャー 急速充電 シガーソケット USB",
            "車載スマホホルダー ワイヤレス充電 自動開閉",
            "紛失防止タグ スマートトラッカー",
            "モバイルモニター 15.6インチ IPS フルHD",
            "小型プロジェクター モバイル 天井投影",
            "レーザーポインター プレゼン用 グリーンレーザー",
            "HDMI切替器 4K 60Hz 双方向 リモコン",
            "スマートプロジェクター Android搭載 静音",
            "スマホ用 ジンバル スタビライザー 自動追尾",
            "LED リングライト 三脚 撮影用 卓上",
            "アクションカメラ 小型 4K 防水",
            "デジタルフォトフレーム WiFi対応 高解像度",
            "スマートグラス ウェアラブルディスプレイ",
            "スマートリモコン 学習リモコン WiFi 赤外線",
            "スマートプラグ タイマー付き コンセント WiFi",
            "見守りカメラ ペットカメラ WiFi 暗視 動体検知",
            "スマート体重計 体組成計 スマホ連動 高精度",
            "Wi-Fi中継器 無線LAN コンセント直挿し 高速",
            "スマートLED電球 調光調色 Alexa対応 E26",
            "スマート温湿度計 Bluetooth デジタル 室内",
            "スマート南京錠 指紋認証 防犯 小型",
            "スマートカーテン 自動開閉 タイマー設定",
            "スマートタグ スマホ連動 キーファインダー",
            "セラミックファンヒーター 人感センサー 小型 省エネ",
            "パネルヒーター 足元 折りたたみ デスク下",
            "電気毛布 ひざ掛け 洗える USB給電",
            "充電式カイロ モバイルバッテリー機能 両面発熱",
            "フットヒーター 足温器 足元暖房 デスクワーク",
            "電気スリッパ コードレス 充電式 ぽかぽか",
            "ミニ電気ストーブ 遠赤外線 速暖",
            "卓上加湿器 超音波 静音 大容量 車載",
            "ハイブリッド式加湿器 卓上 アロマ対応",
            "デスク アロマディフューザー 超音波 小型",
            "サーキュレーター 静音 首振り 小型 3D立体",
            "首掛け扇風機 静音 冷却プレート ネッククーラー",
            "ハンディファン 冷却プレート 静音 卓上扇風機",
            "卓上冷風機 小型 水冷 ミストファン",
            "卓上空気清浄機 小型 イオン発生 静音",
            "脱臭機 小型 オゾン発生器 トイレ 玄関",
            "LED デスクライト クランプ 調光調色 タイマー",
            "モニターライト バーライト スクリーン掛け 非対称配光",
            "卓上クリーナー デスク掃除機 コードレス ミニ",
            "超音波洗浄機 メガネ 時計 アクセサリー 小型",
            "カップウォーマー 保温コースター USB 温度調節",
            "電動エアダスター 充電式 強力 ノズル付き",
            "ラベルライター スマホ接続 サーマルプリンター 小型",
            "電動鉛筆削り コードレス USB充電 自動停止",
            "電動ドライバー 小型 ペン型 精密充電式",
            "ペルチェ素子 スマホクーラー 冷却ファン",
            "ホットアイマスク 充電式 シルク 蒸気 自動オフ",
            "ネックマッサージャー 温熱 首掛け EMS コードレス",
            "ハンディマッサージャー 筋膜リリースガン 静音 軽量",
            "電動歯ブラシ 音波振動 充電式 替えブラシ",
            "口腔洗浄器 ジェットウォッシャー コードレス 防水",
            "メンズシェーバー 小型 回転式 旅行用 Type-C",
            "電気シェーバー 往復式 急速充電 3枚刃",
            "鼻毛カッター エチケットカッター 水洗い 静音",
            "毛玉取り器 電動 充電式 6枚刃 強力",
            "小型 ヘアドライヤー 大風量 マイナスイオン 速乾",
            "衣類スチーマー ハンディスチーマー 小型 軽量",
            "布団乾燥機 コンパクト 靴乾燥 ダニ退治",
            "ヘッドスパ 電動 頭皮マッサージ 防水",
            "アイウォーマー 目元エステ エア温熱 Bluetooth音楽",
            "スマートウォッチ 心拍計 血中酸素 睡眠記録",
            "ハンディミスト 美顔器 携帯用 超音波スチーム",
        ],
        "mikke": [
            "ちいかわ ガチャガチャ コンプリート",
            "ちいかわ マスコット ぬいぐるみ",
            "ハチワレ マスコット ぬいぐるみ",
            "うさぎ ちいかわ マスコット",
            "モモンガ ちいかわ ぬいぐるみ",
            "ちいかわ フィギュア コレクション",
            "ナガノのくま マスコット",
            "ポケモン マスコット ぬいぐるみ",
            "ポケモン カプセルトイ フィギュア",
            "ピカチュウ マスコット ポケモンセンター",
            "イーブイ フィギュア コレクション",
            "ポケモン 指人形 ソフビ",
            "ポケモン もちふわ クッション",
            "サンリオ シークレットBOX",
            "シナモロール マスコット ぬいぐるみ",
            "クロミ マスコット フィギュア",
            "ポチャッコ マスコット ぬいぐるみ",
            "ハンギョドン マスコット",
            "サンリオ カプセルトイ めじるしアクセサリー",
            "スーパーマリオ フィギュア コレクション",
            "星のカービィ マスコット ぬいぐるみ",
            "スプラトゥーン3 マスコット",
            "ピクミン フィギュア マスコット",
            "ゼルダの伝説 グッズ フィギュア",
            "どうぶつの森 フィギュア コレクション",
            "スヌーピー カプセルトイ フィギュア",
            "ミッフィー マスコット ぬいぐるみ",
            "お文具といっしょ マスコット",
            "パペットスンスン グッズ マスコット",
            "mofusand えびにゃん マスコット",
            "パンどろぼう フィギュアコレクション",
            "ノンタン フィギュア ガチャ",
            "コジコジ マスコット フィギュア",
            "純喫茶 ミニチュア コレクション ガチャ",
            "地元アイス ミニチュア ガチャ",
            "スクイーズ もちもち キーホルダー",
            "カプセルトイ ケンエレファント ミニチュア",
            "レトロ看板 ミニチュア マグネット",
            "お弁当 ミニチュア ガチャガチャ",
            "ワンピース フィギュア ワールドコレクタブル",
            "呪術廻戦 るかっぷ フィギュア",
            "鬼滅の刃 フィギュア ちょこのせ",
            "僕のヒーローアカデミア ねんどろいど",
            "SPY×FAMILY アーニャ フィギュア",
            "ハイキュー 指の上シリーズ マスコット",
            "ブルーロック マスコット ぬいぐるみ",
            "チェンソーマン ポチタ ぬいぐるみ",
        ],
        "book": [
            "話題のコミック 全巻セット",
            "少年コミック 話題作 全巻",
            "青年コミック おすすめ 全巻セット",
            "ファンタジー 漫画 全巻セット",
            "SF コミック 全巻セット",
            "サスペンス 漫画 おすすめ 全巻",
            "日常系 コミック おすすめ",
            "バトル漫画 名作 全巻セット",
            "スポーツ漫画 全巻セット",
            "ミステリー 漫画 全巻",
            "グルメ 漫画 おすすめ 全巻",
            "異世界 コミカライズ 全巻セット",
            "少女コミック 名作 全巻セット",
            "恋愛漫画 おすすめ 全巻セット",
            "異世界 ライトノベル 全巻セット",
            "転生 ライトノベル 話題作",
            "ファンタジー 小説 ライトノベル",
            "学園 ライトノベル おすすめ",
            "SF ライトノベル 傑作",
            "悪役令嬢 ライトノベル 全巻",
            "スローライフ ライトノベル",
            "ゲーム世界 転生 小説",
            "本屋大賞 受賞作 小説",
            "ミステリー小説 傑作 おすすめ",
            "SF小説 名作 日本",
            "警察小説 おすすめ 文庫",
            "歴史小説 時代小説 傑作",
            "青春小説 感動 文庫",
            "短編小説集 おすすめ",
            "お仕事小説 おすすめ",
            "心理学 入門 新書",
            "教養 新書 ベストセラー",
            "サイエンス 新書 面白い",
            "歴史 新書 おすすめ",
        ]
    }

    def __init__(self, client_id: str = ""):
        self.client_id = client_id or os.environ.get("YAHOO_CLIENT_ID", "")

    def get_random_query(self, target_genre: str = "mono") -> str:
        queries = self.TARGET_QUERIES.get(target_genre, self.TARGET_QUERIES["mono"])
        return random.choice(queries)

    def extract_valid_images_from_item(self, item_url: str, image_id: str) -> List[str]:
        """商品ページおよびCDNから【確実に実在する商品画像】のみを検証して3枚抽出"""
        valid_images = []

        # 1. メイン大画像
        main_l_url = f"https://item-shopping.c.yimg.jp/i/l/{image_id}"
        if is_valid_yahoo_image(main_l_url):
            valid_images.append(main_l_url)

        # 2. 商品ページのHTMLから実在する高解像度画像URLをスクレイピング
        if item_url:
            try:
                req = urllib.request.Request(item_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    
                    # パターンA: タイムスタンプ付きCDN画像 (_d_)
                    cdn_imgs = re.findall(r'https://item-shopping\.c\.yimg\.jp/i/[ngl]/[^\s\"\'\<\>\?]+', html)
                    for c_img in cdn_imgs:
                        if c_img not in valid_images and is_valid_yahoo_image(c_img):
                            valid_images.append(c_img)
                            if len(valid_images) >= 3:
                                break

                    # パターンB: ショップライブラリの高品質商品画像 (shopping.c.yimg.jp/lib/)
                    if len(valid_images) < 3:
                        lib_imgs = re.findall(r'https://shopping\.c\.yimg\.jp/lib/[^\s\"\'\<\>]+\.(?:jpg|png|jpeg)', html)
                        for l_img in lib_imgs:
                            # トップ画像やアイコン等のノイズを除去
                            if not any(skip in l_img for skip in ["top-cat", "icon", "banner", "logo"]):
                                if l_img not in valid_images and is_valid_yahoo_image(l_img):
                                    valid_images.append(l_img)
                                    if len(valid_images) >= 3:
                                        break
            except Exception as e:
                print(f"Error scraping product page images: {e}")

        # 3. それでも3枚に満たない場合、検証済みのメイン画像で補完（no imageを完全防止）
        fallback_img = valid_images[0] if valid_images else f"https://item-shopping.c.yimg.jp/i/l/{image_id}"
        while len(valid_images) < 3:
            valid_images.append(fallback_img)

        return valid_images[:3]

    def search_items(self, query: str = "", hits: int = 20) -> List[Dict[str, Any]]:
        if not self.client_id:
            print("Warning: YAHOO_CLIENT_ID is not configured.")
            return []

        if not query:
            query = "ガジェット"

        params = {
            "appid": self.client_id,
            "query": query,
            "results": min(hits, 30),
            "sort": "-score",
            "in_stock": "true",
            "image_size": 600
        }

        try:
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_items = data.get("hits", [])
                items = []

                for raw in raw_items:
                    name = raw.get("name", "")
                    clean_name = clean_yahoo_title(name)
                    price_val = raw.get("price", 0)
                    price_str = f"{price_val:,}円" if isinstance(price_val, (int, float)) else str(price_val)
                    item_url = raw.get("url", "")
                    item_code = raw.get("code") or raw.get("id") or item_url
                    image_id = raw.get("imageId", "")
                    description = raw.get("description", "") or raw.get("headLine", "")

                    # 確実に実在するYahoo商品画像を3枚のみ抽出
                    images = self.extract_valid_images_from_item(item_url, image_id)

                    items.append({
                        "name": name,
                        "clean_name": clean_name,
                        "price": price_str,
                        "url": item_url,
                        "item_code": item_code,
                        "image_id": image_id,
                        "images": images,
                        "seller": raw.get("seller", {}).get("name", "Yahoo!ショッピング"),
                        "description": description,
                        "review_rate": raw.get("review", {}).get("rate"),
                        "review_count": raw.get("review", {}).get("count")
                    })
                return items
            else:
                print(f"Yahoo Search error: HTTP {resp.status_code}")
                return []
        except Exception as e:
            print(f"Yahoo Search failed: {e}")
            return []
