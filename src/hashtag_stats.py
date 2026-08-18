"""
Xの「Post Counts（投稿数カウント）」APIを使って、指定したハッシュタグ・
キーワードが直近7日間で何件投稿されているかを調べるスクリプト。

MEO（地図検索対策）でいう「検索回数」そのものではなく、「そのキーワードを
含む投稿が実際にどれくらい行われているか」を見る指標です。Xは検索回数を
公開していないため、投稿の勢いを見る代わりの指標として使います。

このスクリプトは投稿を一切行いません（調査専用）。DRY_RUNの設定に
関わらず動作します。

料金の目安:キーワード1件につき約0.005ドル(Xの従量課金「Counts: Recent」)。
デフォルトの5件なら1回の実行で約0.025ドルです。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import get_client, logger  # noqa: E402

# 調べたいハッシュタグ・キーワードのデフォルト一覧。
# GitHub Actionsの「Run workflow」実行時に入力欄で指定すれば、
# そちらが優先されます(カンマ区切り)。
DEFAULT_KEYWORDS = [
    "#同人ゲーム",
    "#レトロゲーム",
    "#ゲームレビュー",
    "#C109",
    "#コミケ",
]


def get_keywords() -> list:
    env_value = os.getenv("HASHTAGS")
    if env_value and env_value.strip():
        return [k.strip() for k in env_value.split(",") if k.strip()]
    return DEFAULT_KEYWORDS


def main():
    client = get_client()
    keywords = get_keywords()

    print(f"{'キーワード':<16}{'直近7日間の投稿数':>18}")
    print("-" * 40)

    for keyword in keywords:
        try:
            response = client.get_recent_tweets_count(query=keyword)
            total = 0
            if response.meta:
                total = response.meta.get("total_tweet_count", 0)
            elif response.data:
                total = sum(bucket["tweet_count"] for bucket in response.data)
            print(f"{keyword:<16}{total:>15,}件")
        except Exception as exc:  # noqa: BLE001
            logger.error("「%s」の件数取得に失敗しました: %s", keyword, exc)


if __name__ == "__main__":
    main()
