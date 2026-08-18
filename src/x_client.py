"""
X（旧Twitter）への投稿をまとめて扱う共通モジュール。

DRY_RUN=true の間は、実際にはXへ投稿せず、内容を画面に表示するだけです。
必ず DRY_RUN=true の状態で一通り動作確認してから、
本番投稿（DRY_RUN=false）に切り替えてください。
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rakunou-x-automation")


def _is_dry_run() -> bool:
    return os.getenv("DRY_RUN", "true").strip().lower() in ("1", "true", "yes")


def get_client():
    """
    tweepy.Client を作成して返します。
    DRY_RUN=true のときは、実際の認証は行わず None を返します
    （呼び出し側で dry run 用の分岐をしているため、通常はこの関数を
    呼ばなくても post_tweet() だけで動作確認ができます）。
    """
    import tweepy

    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    missing = [
        name
        for name, value in [
            ("X_API_KEY", api_key),
            ("X_API_SECRET", api_secret),
            ("X_ACCESS_TOKEN", access_token),
            ("X_ACCESS_TOKEN_SECRET", access_token_secret),
        ]
        if not value or value.startswith("your_")
    ]
    if missing:
        logger.error(
            "以下のAPIキーが.envに設定されていません: %s\n"
            ".env.example を参考に .env ファイルを作成してください。",
            ", ".join(missing),
        )
        sys.exit(1)

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def weighted_length(text: str) -> int:
    """
    Xの文字数カウントを近似計算します。

    Xでは、日本語・中国語・韓国語などの文字は「2文字分」としてカウントされ、
    英数字などは「1文字分」としてカウントされます（2017年の280文字化の際も、
    日本語ツイートは実質140文字までとされたのはこのためです）。
    ここではASCII文字（英数字・半角記号）を1、それ以外（日本語など）を2として
    近似計算しています。完全に正確な計算ではありませんが、実用上十分な精度です。
    """
    return sum(1 if ord(ch) < 128 else 2 for ch in text)


def post_tweet(text: str) -> None:
    """
    1件のツイートを投稿します。
    DRY_RUN=true のときは、実際には投稿せずログに内容を表示するだけです。
    """
    length = weighted_length(text)
    if length > 280:
        logger.warning(
            "投稿文がXの文字数上限を超えている可能性があります（換算%d文字）。内容を短くしてください。",
            length,
        )

    if _is_dry_run():
        logger.info("[DRY RUN] 実際には投稿していません。内容だけ表示します:\n---\n%s\n---", text)
        return

    client = get_client()
    try:
        response = client.create_tweet(text=text)
        logger.info("投稿しました: tweet_id=%s", response.data.get("id"))
    except Exception as exc:  # noqa: BLE001
        logger.error("投稿に失敗しました: %s", exc)
        raise
