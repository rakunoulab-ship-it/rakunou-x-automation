"""
公開したnote記事を、Xで告知投稿するスクリプト。

note側には「記事を公開したら自動でXに投稿される」という機能がないため、
記事を公開したあと、GitHub Actionsの手動実行（workflow_dispatch）から
このスクリプトを呼び出して、Xへの告知ツイートを行う。

記事タイトルは、渡されたURL先のページからOGP情報（og:title）を使って
自動取得する。取得に失敗した場合は、タイトルなしで投稿する
（存在しない・誤ったタイトルを投稿してしまう事故を防ぐため）。
"""

import os
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from x_client import post_tweet, logger  # noqa: E402

# note記事のURLを貼るとXがリンクカード（記事のOGP画像つき）を自動生成するため、
# ここではゲームニュースまとめ用のブランド画像は添付しない。


def fetch_og_title(url: str):
    """記事ページのOGPタイトル（og:title）を取得する。取得できなければNoneを返す。"""
    try:
        response = requests.get(
            url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(
            "記事ページの取得に失敗しました（%s）。タイトルなしで投稿します。", exc
        )
        return None

    match = re.search(
        r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']',
        response.text,
        re.IGNORECASE,
    )
    if not match:
        logger.warning("OGPタイトルが見つかりませんでした。タイトルなしで投稿します。")
        return None

    title = match.group(1)
    # noteの記事タイトルは末尾に「｜note」やアカウント名が付くことがあるため取り除く
    title = re.sub(r"\s*[｜|]\s*note.*$", "", title).strip()
    return title or None


def build_tweet_text(url: str, comment: str) -> str:
    if comment:
        lead = comment
    else:
        title = fetch_og_title(url)
        lead = f"『{title}』を公開しました！" if title else "新しい記事を公開しました！"

    return f"📝 {lead}\n{url}\n#note #ゲーム情報 #楽脳研究所"


def main():
    url = os.environ.get("NOTE_URL", "").strip()
    comment = os.environ.get("NOTE_COMMENT", "").strip()

    if not url:
        logger.error("記事URLが指定されていません（NOTE_URL）。処理を中止します。")
        sys.exit(1)

    text = build_tweet_text(url, comment)
    logger.info("note記事の告知投稿を行います: %s", url)
    post_tweet(text)


if __name__ == "__main__":
    main()
