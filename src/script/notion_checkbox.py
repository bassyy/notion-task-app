import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import json

# .envファイルを読み込む
load_dotenv()

# 環境変数からデータを取得
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')
JSON_PATH = os.getenv("JSON_PATH")

# ヘッダーの設定
headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# jsonファイルの読み取り
with open(JSON_PATH, 'r') as file:
    notion_columns = json.load(file)

# 今日の日付を取得
today = datetime.now().date()

def get_database_items(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {
        "filter": {
            "and": [
                {"property": notion_columns["date"],"date": {"before": today.isoformat()}},
                {"property": notion_columns["status"],"status": {"does_not_equal": "保留"}},
                {"property": notion_columns["checkbox"], "checkbox": {"equals": False}}
            ]
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()['results']

def update_checkbox_property(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {notion_columns["checkbox"]: {"checkbox": True}}
    }

    response = requests.patch(url, headers=headers, json=payload)

# データベースのアイテムを取得してチェックボックスを更新
items = get_database_items(DATABASE_ID)
for item in items:
    update_checkbox_property(item['id'])