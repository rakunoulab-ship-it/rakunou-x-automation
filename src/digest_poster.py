"""
その日のダイジェストページ（GitHub Pagesで公開済み）へのリンクを、Xに投稿するスクリプト。

digest_generator.py が先に実行され、ページが正常に公開されていることを前提とする。
ページがまだ存在しない（19時の生成が失敗した等）場合は、投稿せずに終了する
（存在しないリンクを投稿してしまう事故を防ぐため）。
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import post_tweet, logger  # noqa: E402

JST = ZoneInfo("Asia/Tokyo")

# GitHub Pagesのベースになるベース。リポジトリ名やアカウント名を変更した場合はここも更新する。
PAGES_BASE_URL = os.getenv(
    "PAGES_BASE_URL", "https://rakunoulab-ship-it.github.io/rakunou-x-automation"
)


def page_exists(url: str) -> bool:
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException as exc:
        logger.warning("ページの存在確認に失敗しました: %s", exc)
        return False


def main():
    now_jst = datetime.now(JST)
    date_path = now_jst.strftime("%Y-%m-%d")
    date_label = f"{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    url = f"{PAGES_BASE_URL}/digest/{date_path}.html"

    if not page_exists(url):
        logger.warning(
            "本日分のダイジェストページがまだ公開されていません（%s）。投稿をスキップします。",
            url,
        )
        return

    text = f"🎮 {date_label}のゲームニュースまとめはこちら\n{url}\n##ゲーム情報　#ゲーム　#楽脳研究所"
    post_tweet(text)


if __name__ == "__main__":
    main()
