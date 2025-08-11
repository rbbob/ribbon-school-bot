import os
import json
import requests
from flask import Flask, request, abort, jsonify, render_template, redirect, session
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from functools import wraps
import PyPDF2
from werkzeug.utils import secure_filename
from database import *

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

# 環境変数から設定を読み込む
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
openai_api_key = os.environ['OPENAI_API_KEY']
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')  # 環境変数で設定

# アップロード設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# アップロードフォルダの作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 管理者認証デコレータ
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

# 学校情報を取得
def get_school_info():
    faq_data = get_faq_data()
    pdf_content = get_pdf_content()
    
    faq_text = "\n".join([f"- {k}: {v}" for k, v in faq_data.items()])
    
    return f"""
あなたはリボンスクールの受付アシスタントです。
以下の情報を基に、お客様の質問に親切で分かりやすく答えてください。

【基本情報】
- 体験レッスン：無料、所要時間約1時間
- 場所：大阪府大阪市西成区玉出中1-12-23
- 電話：06-6651-3832

【FAQ情報】
{faq_text}

【追加情報（PDFより）】
{pdf_content[:2000]}

【対応方針】
- 明るく親しみやすい口調で
- 絵文字を適度に使用（😊など）
- FAQにない質問の場合も、できる限り親切に回答
- 詳細は電話問い合わせを案内
"""

def call_chatgpt(user_message, user_id):
    """ChatGPT APIを呼び出す"""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": get_school_info()},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content']
        
        # FAQに含まれない質問かチェック
        faq_data = get_faq_data()
        found_in_faq = any(keyword in user_message for keyword in faq_data.keys())
        
        # FAQにない質問は記録
        if not found_in_faq and len(user_message) > 5:
            add_unanswered_question(user_message, user_id)
        
        return reply
        
    except Exception as e:
        print(f"ChatGPT APIエラー: {e}")
        return "申し訳ございません。現在システムに問題が発生しています。お手数ですが、お電話（06-6651-3832）でお問い合わせください。"

# ===== 通常のLINE Bot エンドポイント =====

@app.route("/")
def hello():
    return "リボンスクールBot（管理画面付き）が稼働中です！<br><a href='/admin'>管理画面</a>"

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
    user_id = event.source.user_id
    print(f"受信: {user_message} (from: {user_id})")
    
    # ChatGPTに質問
    reply_message = call_chatgpt(user_message, user_id)
    print(f"返信: {reply_message[:50]}...")
    
    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

# ===== 管理画面エンドポイント =====

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin')
        return '''
            <h2>パスワードが違います</h2>
            <a href="/admin/login">戻る</a>
        '''
    
    return '''
        <style>
            body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f5f5f5; }
            .login-box { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            input { padding: 10px; margin: 10px 0; width: 200px; }
            button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        </style>
        <div class="login-box">
            <h2>管理画面ログイン</h2>
            <form method="post">
                <input type="password" name="password" placeholder="パスワード" required><br>
                <button type="submit">ログイン</button>
            </form>
        </div>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

# ===== 管理画面API =====

@app.route('/admin/api/faq', methods=['GET', 'POST'])
@admin_required
def api_faq():
    if request.method == 'GET':
        return jsonify(get_faq_data())
    
    elif request.method == 'POST':
        data = request.json
        faq_data = get_faq_data()
        faq_data[data['keyword']] = data['answer']
        save_faq_data(faq_data)
        return jsonify({'success': True})

@app.route('/admin/api/faq/<keyword>', methods=['PUT', 'DELETE'])
@admin_required
def api_faq_item(keyword):
    faq_data = get_faq_data()
    
    if request.method == 'PUT':
        data = request.json
        if keyword in faq_data:
            del faq_data[keyword]
        faq_data[data['keyword']] = data['answer']
        save_faq_data(faq_data)
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        if keyword in faq_data:
            del faq_data[keyword]
            save_faq_data(faq_data)
        return jsonify({'success': True})

@app.route('/admin/api/questions')
@admin_required
def api_questions():
    return jsonify(get_unanswered_questions())

@app.route('/admin/api/questions/<int:question_id>', methods=['DELETE'])
@admin_required
def api_delete_question(question_id):
    delete_unanswered_question(question_id)
    return jsonify({'success': True})

@app.route('/admin/api/upload-pdf', methods=['POST'])
@admin_required
def api_upload_pdf():
    try:
        if 'pdf' not in request.files:
            return jsonify({'success': False, 'error': 'ファイルがありません'})
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # PDFからテキストを抽出
            pdf_text = ""
            with open(filepath, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
            
            # テキストを保存
            save_pdf_content(pdf_text)
            
            # PDFファイルを削除（テキストのみ保存）
            os.remove(filepath)
            
            return jsonify({'success': True, 'message': f'{len(pdf_text)}文字を抽出しました'})
        
        return jsonify({'success': False, 'error': '無効なファイル形式です'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
