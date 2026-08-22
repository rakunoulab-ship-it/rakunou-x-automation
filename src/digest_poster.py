"""
その日のダイジェストページ（GitHub Pagesで公開済み）へのリンクを、Xに投稿するスクリプト。

digest_generator.py が先に実行され、ページが正常に公開されていることを前提とする。
ページがまだ存在しない（19時の生成が失敗した等）場合は、投稿せずに終了する
（存在しないリンクを投稿してしまう事故を防ぐため）。

また、GitHub Actionsのスケジュール実行はタイミングが遅れることがあり、手動実行と
スケジュール実行が両方動いてしまう（＝同じ内容を2回投稿してしまう）ことがあるため、
「その日すでに投稿済みかどうか」を data/posted_digest_log.json に記録し、
二重投稿を防ぐ。
"""

import json
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

# 投稿に添える固定のブランド画像（assets/make_brand_image.py で生成したもの）
BRAND_IMAGE_PATH = str(
    Path(__file__).resolve().parent.parent / "assets" / "brand_image.png"
)

# 「その日すでに投稿済みか」を記録するログファイル
POSTED_LOG_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "posted_digest_log.json"
)


def page_exists(url: str) -> bool:
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException as exc:
        logger.warning("ページの存在確認に失敗しました: %s", exc)
        return False


def load_posted_dates() -> set:
    if not POSTED_LOG_PATH.exists():
        return set()
    try:
        data = json.loads(POSTED_LOG_PATH.read_text(encoding="utf-8"))
        return set(data.get("posted_dates", []))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("投稿記録の読み込みに失敗しました（無視して続行します）: %s", exc)
        return set()


def save_posted_dates(posted_dates: set) -> None:
    POSTED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSTED_LOG_PATH.write_text(
        json.dumps({"posted_dates": sorted(posted_dates)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    now_jst = datetime.now(JST)
    date_path = now_jst.strftime("%Y-%m-%d")
    date_label = f"{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    posted_dates = load_posted_dates()
    if date_path in posted_dates:
        logger.info(
            "本日（%s）分はすでに投稿済みのため、投稿をスキップします"
            "（GitHub Actionsのスケジュール遅延により、手動実行とスケジュール実行が"
            "重複した可能性があります）。",
            date_path,
        )
        return

    url = f"{PAGES_BASE_URL}/digest/{date_path}.html"

    if not page_exists(url):
        logger.warning(
            "本日分のダイジェストページがまだ公開されていません（%s）。投稿をスキップします。",
            url,
        )
        return

    text = f"🎮 {date_label}のゲームニュースまとめはこちら\n{url}\n#ゲーム情報 #ゲーム #楽脳研究所"
    posted = post_tweet(text, image_path=BRAND_IMAGE_PATH)

    if posted:
        posted_dates.add(date_path)
        save_posted_dates(posted_dates)


if __name__ == "__main__":
    main()
