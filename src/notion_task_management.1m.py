#!/Users/p181/.pyenv/versions/3.11.6/bin/python3

import requests
import json
import sys, os
from dotenv import load_dotenv
import subprocess
from datetime import datetime

# .envファイルを読み込む
load_dotenv()

# 環境変数からNotion API トークンとデータベースID、およびZenityスクリプトのパスを取得
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')
ZENITY_SCRIPT_PATH = os.getenv('ZENITY_SCRIPT_PATH')
PYTHON_PATH = os.getenv('PYTHON_PATH')
SCRIPT_PATH = os.path.abspath(__file__)

# Notion APIのエンドポイント
database_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
page_url = "https://api.notion.com/v1/pages"
headers = {
    "Notion-Version": "2022-06-28",
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json"
}

# 期限をISO 8601形式に変換
def change_deadline(deadline):
    if deadline:
        try:
            deadline = datetime.strptime(deadline, "%Y/%m/%d").strftime("%Y-%m-%d")
        except ValueError:
            print("日付形式が正しくありません。")
            return
    return deadline

def run_zenity(script_path):
    result = subprocess.run([script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip().split("|")

def fetch_tasks():
    payload = {
        "filter": {
            "property": "今日やる",
            "checkbox": {
                "equals": True
            }   
        },
        "sorts": [
            {
                "property": "優先度",
                "direction": "ascending"
            }
        ]
    }

    response = requests.post(database_url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 401:
        print("認証エラー: APIトークンまたはデータベースのアクセス権限を確認してください。")
        print(response.text)
    else:
        return response.json()

def add_task():
    dialog_result = run_zenity(ZENITY_SCRIPT_PATH)

    task_name = dialog_result[0].strip()
    deadline = dialog_result[1].strip()
    memo = dialog_result[2].strip()

    if not task_name:
        print("タスク名は必須です。")
        return


    deadline = change_deadline(deadline)

    new_task = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "タスク名": {
                "title": [
                    {
                        "text": {
                            "content": task_name
                        }
                    }
                ]
            },
            "今日やる": {
                "checkbox": True
            }
        }
    }

    if deadline:
        new_task["properties"]["期限"] = {
            "date": {
                "start": deadline
            }
        }

    if memo:
        new_task["properties"]["メモ"] = {
            "rich_text": [
                {
                    "text": {
                        "content": memo
                    }
                }
            ]
        }

    response = requests.post(page_url, headers=headers, data=json.dumps(new_task))

    if response.status_code == 200:
        print("タスクが正常に追加されました。")
    else:
        print("タスクの追加に失敗しました。")
        print(response.text)

def delete_task(task_id):
    url = f"https://api.notion.com/v1/blocks/{task_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        print("タスクが正常に削除されました。")
    else:
        print("タスクの削除に失敗しました。")
        print(response.text)

def edit_task(task_id):
    dialog_result = run_zenity(ZENITY_SCRIPT_PATH)

    task_name = dialog_result[0].strip()
    deadline = dialog_result[1].strip()
    memo = dialog_result[2].strip()

    updated_task = {"properties": {}}

    deadline = change_deadline(deadline)

    if task_name:
        updated_task["properties"]["タスク名"] = {
            "title": [
                {
                    "text": {
                        "content": task_name
                    }
                }
            ]
        }
    if deadline:
        updated_task["properties"]["期限"] = {
            "date": {
                "start": deadline
            }
        }
    if memo:
        updated_task["properties"]["メモ"] = {
            "rich_text": [
                {
                    "text": {
                        "content": memo
                    }
                }
            ]
        }

    url = f"https://api.notion.com/v1/pages/{task_id}"
    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))

    if response.status_code == 200:
        print("タスクが正常に更新されました。")
    else:
        print("タスクの更新に失敗しました。")
        print(response.text)

def toggle_today(task_id):
    updated_task = {
        "properties": {
            "今日やる": {
                "checkbox": False
            }
        }
    }
    
    url = f"https://api.notion.com/v1/pages/{task_id}"
    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))
    
    if response.status_code == 200:
        print("今日やるのチェックが外されました。")
    else:
        print("今日やるのチェックを外すのに失敗しました。")
        print(response.text)

def change_status(task_id, new_status):
    updated_task = {
        "properties": {
            "ステータス": {
                "status": {
                    "name": new_status
                }
            }
        }
    }

    url = f"https://api.notion.com/v1/pages/{task_id}"
    response = requests.patch(url, headers=headers, data=json.dumps(updated_task))

    if response.status_code == 200:
        print("ステータスが正常に変更されました。")
    else:
        print("ステータスの変更に失敗しました。")
        print(response.text)

def main():
    print(f":book.fill: タスク一覧 | dropdown=true")
    print("---")
    print(f"タスク一覧を表示 | href=https://www.notion.so/{DATABASE_ID}")
    print("---")
    tasks = fetch_tasks()
    if tasks:
        for task in tasks.get("results", []):
            task_name = task["properties"]["タスク名"]["title"][0]["text"]["content"]
            task_id = task["id"]

            # プロパティの存在を確認
            priority = "未設定"
            priority_icon = "⚪️"  # デフォルトの低い優先度のアイコン
            if "優先度" in task["properties"] and task["properties"]["優先度"].get("select"):
                priority = task["properties"]["優先度"]["select"]["name"]
                if priority == "高":
                    priority_icon = "🔴"  # 高い優先度のアイコン
                elif priority == "中":
                    priority_icon = "🟠"  # 中の優先度のアイコン

            status = "未設定"
            status_icon = "⚪️"  # デフォルトの未着手アイコン
            if "ステータス" in task["properties"] and task["properties"]["ステータス"].get("status"):
                status = task["properties"]["ステータス"]["status"]["name"]
                if status == "未着手":
                    status_icon = "🔴"  # 未着手の場合のアイコン
                elif status == "進行中":
                    status_icon = "🟠"  # 進行中の場合のアイコン
                elif status == "完了":
                    status_icon = "🟢"  # 完了の場合のアイコン

            deadline = "なし"
            if "期限" in task["properties"] and task["properties"]["期限"].get("date"):
                deadline = task["properties"]["期限"]["date"]["start"]

            memo = "なし"
            memo_icon = "⚪️"  # デフォルトのメモがないアイコン
            if "メモ" in task["properties"] and task["properties"]["メモ"].get("rich_text"):
                memo = task["properties"]["メモ"]["rich_text"][0]["text"]["content"]
                memo_icon = "📝"  # メモが設定されている場合のアイコン

            print(f"{task_name} | href=https://www.notion.so/aidemy/{task_id}")
            print(f"--{priority_icon} 優先度: {priority} | terminal=false")
            print(f"--{status_icon} ステータス: {status} | terminal=false")
            print(f"--期限: {deadline} | terminal=false")
            print(f"--{memo_icon} メモ: {memo} | terminal=false")
            print(f"--今日やるのチェックを外す | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='toggle_today' param3='{task_id}' terminal=false refresh=true")
            print(f"--ステータスを未着手に変更 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='未着手' terminal=false refresh=true")
            print(f"--ステータスを進行中に変更 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='進行中' terminal=false refresh=true")
            print(f"--ステータスを完了に変更 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='change_status' param3='{task_id}' param4='完了' terminal=false refresh=true")
            print(f"--削除 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='delete' param3='{task_id}' terminal=false refresh=true")
            print(f"--編集 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='edit' param3='{task_id}' terminal=false refresh=true")
    print("---")
    print(f"新しいタスクを追加 | bash='{PYTHON_PATH}' param1='{SCRIPT_PATH}' param2='add' terminal=false refresh=true")
    print("更新 | refresh=true")

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
        elif command == "toggle_today" and len(sys.argv) == 3:
            task_id = sys.argv[2]
            toggle_today(task_id)
        elif command == "change_status" and len(sys.argv) == 4:
            task_id = sys.argv[2]
            new_status = sys.argv[3]
            change_status(task_id, new_status)
    else:
        main()
