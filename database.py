import json
import os
from datetime import datetime

# データファイルのパス
FAQ_FILE = 'faq_data.json'
QUESTIONS_FILE = 'unanswered_questions.json'
PDF_CONTENT_FILE = 'pdf_content.txt'

def load_json_file(filename, default=None):
    """JSONファイルを読み込む"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"ファイル読み込みエラー: {filename} - {e}")
    return default if default is not None else {}

def save_json_file(filename, data):
    """JSONファイルに保存"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"ファイル保存エラー: {filename} - {e}")
        return False

def get_faq_data():
    """FAQ データを取得"""
    return load_json_file(FAQ_FILE, {
        "体験": "体験レッスンは無料で受けられます。所要時間は約1時間です。",
        "料金": "単発レッスンは3,500円〜、月謝制（月4回）は6,000円〜です。",
        "初心者": "もちろん大丈夫です！9割以上の生徒さんが初心者からスタートしています。",
        "持ち物": "ノートと鉛筆で大丈夫です。",
        "予約": "LINEメッセージまたは電話（06-6651-3832）でご予約ください。",
        "場所": "大阪府大阪市西成区玉出中1-12-23",
        "時間": "平日10:00-18:00、土曜日午前中です。日曜・祝日はお休みです。"
    })

def save_faq_data(faq_data):
    """FAQデータを保存"""
    return save_json_file(FAQ_FILE, faq_data)

def get_unanswered_questions():
    """未回答質問を取得"""
    return load_json_file(QUESTIONS_FILE, [])

def add_unanswered_question(question, user_id):
    """未回答質問を追加"""
    questions = get_unanswered_questions()
    questions.append({
        'id': len(questions) + 1,
        'timestamp': datetime.now().isoformat(),
        'question': question,
        'user_id': user_id,
        'status': 'pending'
    })
    save_json_file(QUESTIONS_FILE, questions)

def delete_unanswered_question(question_id):
    """未回答質問を削除"""
    questions = get_unanswered_questions()
    questions = [q for q in questions if q.get('id') != question_id]
    save_json_file(QUESTIONS_FILE, questions)

def get_pdf_content():
    """PDFコンテンツを取得"""
    try:
        if os.path.exists(PDF_CONTENT_FILE):
            with open(PDF_CONTENT_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"PDFコンテンツ読み込みエラー: {e}")
    return ""

def save_pdf_content(content):
    """PDFコンテンツを保存"""
    try:
        with open(PDF_CONTENT_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"PDFコンテンツ保存エラー: {e}")
        return False
