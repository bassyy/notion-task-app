#!/bin/bash


# タスク名、期限、メモを取得するフォームの表示
form_result=$(
    zenity --forms \
    --title="新しい$1" \
    --text="$1の詳細を入力してください。" \
    --add-entry="$1" \
    --add-calendar="$2" \
    --add-entry="$3"
    )

# 入力結果をPythonスクリプトに渡す
echo "$form_result"