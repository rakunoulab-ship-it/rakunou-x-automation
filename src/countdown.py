"""
冬コミ（C109）に向けたカウントダウン投稿を自動化するスクリプト。

.env の COUNTDOWN_START_DATE より前は何も投稿しません。
COUNTDOWN_START_DATE 〜 EVENT_DATE前日までは「あと◯日」の投稿、
開催期間中（EVENT_DATE〜+2日、C109は3日間開催のため）は「◯日目」の投稿、
それ以降は何も投稿しません。
"""

import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import post_tweet, logger  # noqa: E402

EVENT_DURATION_DAYS = int(os.getenv("EVENT_DURATION_DAYS", "3"))


def _parse_date(env_value: str, label: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(env_value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        logger.error(
            "%s の日付形式が正しくありません（YYYY-MM-DD形式で.envに設定してください）: %r",
            label,
            env_value,
        )
        sys.exit(1)


def build_tweet_text(today: datetime.date, start_date: datetime.date, event_date: datetime.date, circle_space: str) -> str | None:
    event_end = event_date + datetime.timedelta(days=EVENT_DURATION_DAYS - 1)

    if today < start_date:
        return None

    if today < event_date:
        days_left = (event_date - today).days
        space_line = f"配置：{circle_space}\n" if circle_space and circle_space != "未定" else ""
        return (
            f"🎮 冬コミ（C109）まであと{days_left}日！\n"
            f"楽脳研究所は新刊を準備中です。\n"
            f"{space_line}"
            f"#C109 #冬コミ #同人サークル"
        )

    if today <= event_end:
        day_number = (today - event_date).days + 1
        space_line = f"配置：{circle_space}\n" if circle_space and circle_space != "未定" else ""
        return (
            f"🎮 本日はC109 {day_number}日目です！\n"
            f"楽脳研究所は本日も新刊を頒布しております。\n"
            f"{space_line}"
            f"ぜひお立ち寄りください。\n"
            f"#C109 #冬コミ"
        )

    return None


def main():
    start_date = _parse_date(os.getenv("COUNTDOWN_START_DATE"), "COUNTDOWN_START_DATE")
    event_date = _parse_date(os.getenv("EVENT_DATE"), "EVENT_DATE")
    circle_space = os.getenv("CIRCLE_SPACE", "未定")

    today = datetime.date.today()
    text = build_tweet_text(today, start_date, event_date, circle_space)

    if text is None:
        logger.info("本日（%s）はカウントダウン投稿の対象期間外です。", today.isoformat())
        return

    post_tweet(text)


if __name__ == "__main__":
    main()
