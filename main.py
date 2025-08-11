import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 環境変数から設定を読み込む
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
openai_api_key = os.environ['OPENAI_API_KEY']

# リボンスクールの基本情報（ここにPDFの内容を追加）
SCHOOL_INFO = """
あなたはリボンスクールの受付アシスタントです。
以下の情報を基に、お客様の質問に親切で分かりやすく答えてください。

【基本情報】
- 体験レッスン：無料、所要時間約1時間
- 初心者：9割以上が初心者からスタート、基礎から丁寧に指導
- 持ち物：ノートと鉛筆で大丈夫
- 料金：単発レッスン3,500円〜、月謝制（月4回）6,000円〜
- 予約：LINEメッセージまたは電話（06-6651-3832）
- 場所：大阪府大阪市西成区玉出中1-12-23
- 営業時間：平日10:00-18:00、土曜日午前中、日曜・祝日休み

【追加情報】
ここにPDFから抽出したテキストを追加してください。
例：
- コース詳細：初級、中級、上級、講師養成コース
- 資格取得：リボンアート認定資格、講師資格
- 特典：初回体験無料、友達紹介割引
- イベント：季節のワークショップ、作品展示会

【対応方針】
- 明るく親しみやすい口調で
- 絵文字を適度に使用（😊など）
- 不明な点は電話でのお問い合わせを案内
"""

def call_chatgpt(user_message):
    """ChatGPT APIを呼び出す"""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SCHOOL_INFO},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"ChatGPT APIエラー: {e}")
        # エラー時のフォールバック
        return "申し訳ございません。現在システムに問題が発生しています。お手数ですが、お電話（06-6651-3832）でお問い合わせください。"

@app.route("/")
def hello():
    return "リボンスクールBotが稼働中です！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature error")
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    print(f"受信: {user_message}")
    
    # ChatGPTに質問
    reply_message = call_chatgpt(user_message)
    print(f"返信: {reply_message[:50]}...")  # 最初の50文字だけログ出力
    
    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
