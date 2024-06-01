#!/bin/bash

# タスク名、期限、メモを取得するフォームの表示
form_result=$(zenity --forms --title="新しいタスク" --text="タスクの詳細を入力してください。" \
    --add-entry="タスク名" \
    --add-calendar="期限" \
    --add-entry="メモ")

# Zenityフォームの結果を標準出力に表示
echo "$form_result"
