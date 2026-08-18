"""
Xの自分のアカウント(楽脳研究所)のフォロワー数を、毎日記録しておくスクリプト。

X Premiumに入らなくても、フォロワー数の推移を自分たちで記録・確認できるように
するためのもの。X APIの「自分のデータを取得する」操作(Owned Reads)は
1回あたり約0.001ドルとほぼ無料なので、毎日実行してもコストはごくわずか。

記録先: data/follower_history.csv
同じ日に複数回実行しても、その日の行は上書きされるだけで重複しない。
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import get_client, logger  # noqa: E402

JST = ZoneInfo("Asia/Tokyo")

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "follower_history.csv"

FIELDNAMES = ["date", "followers_count", "following_count", "tweet_count"]


def fetch_metrics() -> dict:
    client = get_client()
    response = client.get_me(user_fields=["public_metrics"])
    metrics = response.data.public_metrics
    return {
        "followers_count": metrics["followers_count"],
        "following_count": metrics["following_count"],
        "tweet_count": metrics["tweet_count"],
    }


def load_rows() -> list:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    today_str = datetime.now(JST).strftime("%Y-%m-%d")

    metrics = fetch_metrics()
    logger.info(
        "フォロワー数: %s / フォロー数: %s / 投稿数: %s",
        metrics["followers_count"],
        metrics["following_count"],
        metrics["tweet_count"],
    )

    rows = load_rows()
    # 同じ日の行があれば置き換え、なければ追加する
    rows = [r for r in rows if r["date"] != today_str]
    rows.append({"date": today_str, **{k: str(v) for k, v in metrics.items()}})
    rows.sort(key=lambda r: r["date"])

    save_rows(rows)
    print(f"記録しました（{today_str}）: {CSV_PATH}")


if __name__ == "__main__":
    main()
