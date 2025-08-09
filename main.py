import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 環境変数から設定を読み込む
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

# よくある質問と回答
FAQ = {
    "体験": "体験レッスンは無料で受けられます。所要時間は約１時間で、必要なことをを学べます。",
    "初心者": "もちろん大丈夫です！9割以上の生徒さんが初心者からスタートしています。基礎から丁寧にお教えします。",
    "持ち物": "ノートを鉛筆で大丈夫です。",
    "料金": "単発レッスンは3,500円～、月謝制（月4回）は6,000円~です。",
    "予約": "このLINEでメッセージをいただくか、お電話（06-6651-3832）でご予約ください。",
    "場所": "大阪府大阪市西成区玉出中1-12-23。",
    "時間": "平日10:00-18:00、土曜日午前中です。日曜・祝日はお休みです。"
}

@app.route("/")
def hello():
    # デバッグ用（後で削除）
    token = os.environ.get('CHANNEL_ACCESS_TOKEN', 'Not Set')
    secret = os.environ.get('CHANNEL_SECRET', 'Not Set')
    return f"リボンスクールBotが稼働中です！<br>Token設定: {'OK' if len(token) > 100 else 'NG'} (長さ: {len(token)})<br>Secret設定: {'OK' if len(secret) > 20 else 'NG'}"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    reply_message = ""
    
    # 複数のキーワードをチェック
    found = False
    for keyword, answer in FAQ.items():
        if keyword in user_message:
            reply_message = answer
            found = True
            break
    
    if not found:
        # どの質問にも当てはまらない場合
        reply_message = """ご質問ありがとうございます😊

以下についてお答えできます：
📍 体験レッスン
📍 初心者の方へ
📍 持ち物
📍 料金
📍 予約方法
📍 場所・アクセス
📍 営業時間
📍 資格取得
📍 コース内容

知りたい内容をメッセージでお送りください。
お急ぎの場合は、お電話（06-6651-3832）でもお問い合わせいただけます。"""
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
