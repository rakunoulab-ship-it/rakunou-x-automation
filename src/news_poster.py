"""
ゲーム関連ニュースをRSSで取得し、Xに自動投稿するスクリプト。

使用しているRSSフィードは以下の3サイトです（2026年8月時点で動作確認済み）。
サイトによってはRSS配信が終了・変更されることがあるため、
定期的に動作確認することをおすすめします。

- 4Gamer: https://www.4gamer.net/rss/index.xml
- Game*Spark: https://www.gamespark.jp/rss/index.rdf
- インサイド: https://www.inside-games.jp/rss20/index.rdf

投稿にはリンクを含めるため、X APIの従量課金では
「リンクなし投稿」より高い料金（1件あたり約0.20ドル）がかかります。
.env の MAX_NEWS_POSTS_PER_RUN で、1回の実行あたりの投稿数に上限を設定できます。
"""

import json
import os
import sys
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import post_tweet, weighted_length, logger  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
POSTED_LOG_PATH = BASE_DIR / "data" / "posted_log.json"

# ここにRSSフィードのURLを追加・削除して、情報源をカスタマイズできます。
RSS_FEEDS = [
    ("4Gamer", "https://www.4gamer.net/rss/index.xml"),
    ("Game*Spark", "https://www.gamespark.jp/rss/index.rdf"),
    ("インサイド", "https://www.inside-games.jp/rss20/index.rdf"),
]
# タイトルにこれらの単語が含まれる記事は、ゲーム本体のニュースではないと判断してスキップする。
# インサイドなどのRSSは「フィギュア・グッズ」「アニメ」等、ゲーム以外の話題も
# 同じフィードに混ざって配信されるため、キーワードで簡易的に除外する。
# 実際に紛れ込んだ記事があれば、ここにキーワードを追加していけば精度が上がる。
NG_KEYWORDS = [
    "フィギュア",
    "グッズ",
    "くじ",
    "ステッカー",
    "シール",
    "ぬいぐるみ",
    "アクリルスタンド",
    "コラボカフェ",
    "痛車",
    "プラモデル",
    "声優",
    "舞台化",
    "実写化",
    "アニメ化",
]


def is_game_related(title: str) -> bool:
    """タイトルにNGキーワードが含まれていないかを確認する。"""
    return not any(ng in title for ng in NG_KEYWORDS)
MAX_POSTED_LOG_SIZE = 1000  # posted_log.jsonが際限なく大きくならないようにする上限


def load_posted_links() -> set:
    if not POSTED_LOG_PATH.exists():
        return set()
    with open(POSTED_LOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("posted_news_links", []))


def save_posted_links(links: list) -> None:
    # 古いものから削除して、上限を超えないようにする
    trimmed = links[-MAX_POSTED_LOG_SIZE:]
    with open(POSTED_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump({"posted_news_links": trimmed}, f, ensure_ascii=False, indent=2)


def fetch_new_entries(already_posted: set) -> list:
    """全フィードから、まだ投稿していない記事を新しい順に集める。"""
    candidates = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("フィード取得に失敗しました（%s）: %s", source_name, exc)
            continue

        if parsed.bozo and not parsed.entries:
            logger.warning("フィードを解析できませんでした（%s）: %s", source_name, feed_url)
            continue

        for entry in parsed.entries:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title or link in already_posted:
                continue
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            candidates.append(
                {
                    "source": source_name,
                    "title": title.strip(),
                    "link": link.strip(),
                    "published": published,
                }
            )

    # 発行日時が新しい順に並べ替え（取得できないものは末尾に）
    candidates.sort(key=lambda x: x["published"] or (), reverse=True)
    return candidates


def build_tweet_text(entry: dict) -> str:
    # Xの文字数上限は280（換算文字数）。日本語は1文字が2としてカウントされるため、
    # 単純な文字数ではなく weighted_length() を使って予算を計算する。
    # リンクはt.coで自動短縮され、実際の長さに関わらず一律23文字分としてカウントされる。
    link_budget = 23
    prefix = "🎮 "
    tag = "\n#ゲームニュース"
    fixed_budget = weighted_length(prefix) + weighted_length(tag) + link_budget + 6  # 改行や近似誤差の余白（安全マージン）
    title_budget = 280 - fixed_budget

    title = entry["title"]
    if weighted_length(title) > title_budget:
        # 日本語は1文字=2としてカウントされるので、安全側に倒して半分の文字数を目安に削る
        truncated = []
        used = 0
        for ch in title:
            w = 1 if ord(ch) < 128 else 2
            if used + w > title_budget - 2:  # 「…」の分(2)を残す
                break
            truncated.append(ch)
            used += w
        title = "".join(truncated) + "…"

    return f"{prefix}{title}\n{entry['link']}{tag}"


def main():
    # Secret未登録だと空文字が渡ってくることがあるため、空文字もデフォルト扱いにする
    max_posts = int(os.getenv("MAX_NEWS_POSTS_PER_RUN") or "2")
    already_posted = load_posted_links()

    entries = fetch_new_entries(already_posted)
    if not entries:
        logger.info("新しく投稿できるニュースはありませんでした。")
        return

    to_post = entries[:max_posts]
    newly_posted_links = list(already_posted)

    for entry in to_post:
        text = build_tweet_text(entry)
        logger.info("投稿対象（%s）: %s", entry["source"], entry["title"])
        post_tweet(text)
        newly_posted_links.append(entry["link"])

    save_posted_links(newly_posted_links)
    logger.info("%d件のニュースを処理しました。", len(to_post))


if __name__ == "__main__":
    main()
