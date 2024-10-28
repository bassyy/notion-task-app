#!/Applications/github/notion-task-app/venv/bin/python3

import requests
import json
import sys, os
from dotenv import load_dotenv
import subprocess   
from datetime import datetime

# .envファイルを読み込む
load_dotenv()

# 環境変数からデータを取得
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')

#ファイル名の設定
JSON_FILE_NAME = 'column_setting.json'
ZENITY_FILE_NAME = 'task_editor.sh'

## パスの取得
PYTHON_SCRIPT_PATH = os.path.abspath(__file__)
apps_dir = os.path.dirname(os.path.abspath(PYTHON_SCRIPT_PATH))
notion_task_app_dir = os.path.dirname(os.path.dirname(apps_dir))
ZENITY_SCRIPT_PATH = os.path.join(notion_task_app_dir, 'src', 'script', ZENITY_FILE_NAME)
JSON_PATH = os.path.join(notion_task_app_dir, JSON_FILE_NAME)

# メニューバーに表示するタイトル
MENU_TITLE = 'タスク一覧'

# Notion APIのエンドポイント
database_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
page_url = "https://api.notion.com/v1/pages"
headers = {
    "Notion-Version": "2022-06-28",
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json"
}


# Jsonファイルの読み取り
with open(JSON_PATH, 'r') as file:
    notion_columns = json.load(file)

# 期限をISO 8601形式に変換する関数
def change_deadline(deadline):
    if deadline:
        try:
            deadline = datetime.strptime(deadline, "%Y/%m/%d").strftime("%Y-%m-%d")
            return deadline
        except ValueError:
            print("日付形式が正しくありません。")
            return None

# Zenityの起動する関数
def run_zenity(script_path): 
    command = [
        script_path, 
        notion_columns['title'],
        notion_columns['date'],
        notion_columns['rich_text']
        ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    return result.stdout.strip().split("|")

# Notion DBからデータを取得する関数
def fetch_tasks(ch_box_bool):
    payload = {
        "filter": {
            "and": [
                {"property": notion_columns["status"],"status": {"does_not_equal": "完了"}},
                {"property": notion_columns["status"],"status": {"does_not_equal": "保留"}},
                {"property": notion_columns["checkbox"], "checkbox": {"equals": ch_box_bool}}
            ]
        },
        "sorts": [
            {"property": notion_columns["date"],"direction": "ascending"},  # 日付ソート
            {"property": notion_columns["select"],"direction": "ascending"} # 優先度ソート
        ]
    }

    response = requests.post(database_url, headers=headers, data=json.dumps(payload))

    if response.status_code == 401:
        print("認証エラー: APIトークンまたはデータベースのアクセス権限を確認してください。")
        print(response.text)
    else:
        return response.json()

# タスクを追加する関数
def add_task():
    task_name, deadline, memo = run_zenity(ZENITY_SCRIPT_PATH)

    if not task_name:
        print(f"{notion_columns['title']}は必須です。")
        return

    deadline = change_deadline(deadline)

    new_task = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            notion_columns["title"]:{"title": [{"text": {"content": task_name}}]},
            notion_columns["checkbox"]:{"checkbox": True}
        }
    }

    if deadline:
        new_task["properties"][notion_columns["date"]] = {"date": {"start": deadline}}

    if memo:
        new_task["properties"][notion_columns["rich_text"]] = {"rich_text": [{"text": {"content": memo}}]}

    response = requests.post(page_url, headers=headers, data=json.dumps(new_task))
    check_response_status(response, "追加", "title")

# タスクを削除する関数
def delete_task(task_id):
    url = f"https://api.notion.com/v1/blocks/{task_id}"
    response = requests.delete(url, headers=headers)

    check_response_status(response, "削除", "title")

# タスクを編集する関数
def edit_task(task_id):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    task_name, deadline, memo = run_zenity(ZENITY_SCRIPT_PATH)
    updated_task = {"properties": {}}
    deadline = change_deadline(deadline)

    if task_name:
        updated_task["properties"][notion_columns["title"]] = {"title": [{"text": {"content": task_name}}]}
    if deadline:
        updated_task["properties"][notion_columns["date"]] = {"date": {"start": deadline}}
    if memo:
        updated_task["properties"][notion_columns["rich_text"]] = {"rich_text": [{"text": {"content": memo}}]}

    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))
    check_response_status(response, "更新", "title")

# チェックを外す関数
def uncheck_task(task_id):
    url = f"https://api.notion.com/v1/pages/{task_id}"

    updated_task = {"properties": {notion_columns["checkbox"]: {"checkbox": False}}}
    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))
    
    check_response_status(response, "チェックを外す", "checkbox")

# ステータスを変更する関数
def change_status(task_id, new_status):
    updated_task = {"properties": {notion_columns["status"]: {"status": {"name": new_status}}}}

    url = f"https://api.notion.com/v1/pages/{task_id}"
    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))

    check_response_status(response, "更新", "status")

# レスポンスのステータスを確認する関数
def check_response_status(response, action_name, property_name):
    if response.status_code == 200:
        print(f"{notion_columns[property_name]}が正常に{action_name}されました。")
    else:
        print(f"{notion_columns[property_name]}の{action_name}に失敗しました。")
        print(response.text)


# 実行日より古い期限のタスクを取得する関数
def get_database_items(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    # 今日の日付を取得
    today = datetime.now().date()
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

# チェックボックスをTrueにする関数
def update_checkbox_property(task_id):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    payload = {
        "properties": {notion_columns["checkbox"]: {"checkbox": True}}
    }

    response = requests.patch(url, headers=headers, json=payload)

    # データベースのアイテムを取得してチェックボックスを更新
    items = get_database_items(DATABASE_ID)
    for item in items:
        update_checkbox_property(item['id'])

def main():
    print(f":book.fill: {MENU_TITLE} | dropdown=true")
    print("---")
    print(f"{notion_columns['title']}を追加 | bash='{PYTHON_SCRIPT_PATH}' param2='add' terminal=false refresh=true")
    print(f"Notion DBを表示 | href=https://www.notion.so/{DATABASE_ID}")
    print(f"{notion_columns['title']}を更新 | refresh=true")
    print("---")
    task_chbox_true = fetch_tasks(True)
    task_chbox_false = fetch_tasks(False)

    if task_chbox_true:
        for task in task_chbox_true.get("results", []):

            task_name = task["properties"][notion_columns["title"]]["title"][0]["text"]["content"]
            task_id = task["id"]
            task_url = task["url"]

            # プロパティの存在を確認
            priority = ""
            if notion_columns["select"] in task["properties"] and task["properties"][notion_columns["select"]].get("select"):
                priority = task["properties"][notion_columns["select"]]["select"]["name"]

            status = ""
            if notion_columns["status"] in task["properties"] and task["properties"][notion_columns["status"]].get("status"):
                status = task["properties"][notion_columns["status"]]["status"]["name"]

            deadline = ""
            if notion_columns["date"] in task["properties"] and task["properties"][notion_columns["date"]].get("date"):
                deadline = task["properties"][notion_columns["date"]]["date"]["start"]

            memo = ""
            if notion_columns["rich_text"] in task["properties"] and task["properties"][notion_columns["rich_text"]].get("rich_text"):
                memo = task["properties"][notion_columns["rich_text"]]["rich_text"][0]["text"]["content"]
            
            print(f"{task_name} | href={task_url}")
            print(f"--{notion_columns['status']}を完了に変更 | bash='{PYTHON_SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='完了' terminal=false refresh=true")
            print(f"--編集 | bash='{PYTHON_SCRIPT_PATH}' param2='edit' param3='{task_id}' terminal=false refresh=true")
            print(f"--{notion_columns['select']} : {priority} | terminal=false")
            print(f"--{notion_columns['status']}: {status} | terminal=false")
            print(f"--{notion_columns['date']}: {deadline} | terminal=false")
            print(f"--{notion_columns['rich_text']}: {memo} | terminal=false")
            print(f"--{notion_columns['checkbox']}のチェックを外す | bash='{PYTHON_SCRIPT_PATH}' param2='uncheck_task' param3='{task_id}' terminal=false refresh=true")
            print(f"--{notion_columns['status']}を未着手に変更 | bash='{PYTHON_SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='未着手' terminal=false refresh=true")
            print(f"--{notion_columns['status']}を進行中に変更 | bash='{PYTHON_SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='進行中' terminal=false refresh=true")
            print(f"--削除 | bash='{PYTHON_SCRIPT_PATH}' param2='delete' param3='{task_id}' terminal=false refresh=true")

    if task_chbox_false:
        print("---")
        print(f"{notion_columns['checkbox']}にチェックなし{notion_columns['title']}一覧 | refresh=true")
        for task in task_chbox_false.get("results", []):
            task_name = task["properties"][notion_columns["title"]]["title"][0]["text"]["content"]
            task_id = task["id"]
            task_url = task["url"]
            print(f"--{task_name} | href={task_url}")

    print(f"チェックボックス初期化 | bash='{PYTHON_SCRIPT_PATH}' param2='update_ch_box' param3='{task_id}' terminal=false refresh=true")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "add":
            add_task()
        elif command == "delete" and len(sys.argv) == 3:
            task_id = sys.argv[2]
            delete_task(task_id)
        elif command == "edit" and len(sys.argv) == 3:
            task_id = sys.argv[2]
            edit_task(task_id)
        elif command == "uncheck_task" and len(sys.argv) == 3:
            task_id = sys.argv[2]
            uncheck_task(task_id)
        elif command == "change_status" and len(sys.argv) == 4:
            task_id = sys.argv[2]
            new_status = sys.argv[3]
            change_status(task_id, new_status)
        elif command == "update_ch_box" and len(sys.argv) == 3:
            task_id = sys.argv[2]
            update_checkbox_property(task_id)
    else:
        main()
