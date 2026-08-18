"""
「今日は何の日」形式で、レトロゲームの発売記念日を自動投稿するスクリプト。

data/retro_game_releases.csv に登録されたタイトルの中から、
今日の月日に一致するものを探して投稿します。
一致するデータがない日は、何も投稿せず終了します（エラーではありません）。

このCSVは同梱のサンプルデータです。ファミ通の「今日は何の日？」シリーズや
Wikipediaなどの信頼できる情報源で日付を確認しながら、
少しずつ追加していくことをおすすめします。
"""

import csv
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import post_tweet, logger  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "retro_game_releases.csv"


def load_todays_entries(today: datetime.date) -> list:
    month_day = today.strftime("%m-%d")
    matches = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["month_day"] == month_day:
                matches.append(row)
    return matches


def build_tweet_text(entry: dict, today: datetime.date) -> str:
    years_ago = today.year - int(entry["year"])
    anniversary = f"{years_ago}周年" if years_ago > 0 else "発売日"
    month_str, day_str = entry["month_day"].split("-")
    date_label = f"{int(month_str)}月{int(day_str)}日"
    return (
        f"📅 今日は何の日\n"
        f"{entry['year']}年{date_label}、"
        f"『{entry['title']}』（{entry['platform']}）が発売されました。\n"
        f"本日で{anniversary}です。{entry['note']}\n"
        f"#レトロゲーム #今日は何の日"
    )


def main():
    today = datetime.date.today()
    entries = load_todays_entries(today)

    if not entries:
        logger.info("本日（%s）に該当するレトロゲームの記念日データはありません。", today.isoformat())
        return

    # 複数該当する場合も、投稿しすぎを避けるため1件だけ投稿する
    entry = entries[0]
    text = build_tweet_text(entry, today)
    logger.info("記念日投稿: %s", entry["title"])
    post_tweet(text)


if __name__ == "__main__":
    main()
