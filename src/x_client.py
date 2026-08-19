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
    # GitHub ActionsのSecretsは、登録し忘れると「未設定」ではなく「空文字」として
    # 渡ってくる。os.getenv(..., "true") だと空文字はデフォルト値に置き換わらず、
    # 意図せずDRY_RUNが解除されてしまうため、空文字も「未設定」として扱う。
    value = os.getenv("DRY_RUN") or "true"
    return value.strip().lower() in ("1", "true", "yes")


def _get_credentials() -> dict:
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

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "access_token": access_token,
        "access_token_secret": access_token_secret,
    }


def get_client():
    """
    tweepy.Client（X API v2用）を作成して返します。
    DRY_RUN=true のときは、実際の認証は行わず None を返します
    （呼び出し側で dry run 用の分岐をしているため、通常はこの関数を
    呼ばなくても post_tweet() だけで動作確認ができます）。
    """
    import tweepy

    creds = _get_credentials()
    return tweepy.Client(
        consumer_key=creds["api_key"],
        consumer_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


def get_media_api():
    """
    tweepy.API（X API v1.1用）を作成して返します。
    画像のアップロードは現時点でv1.1エンドポイントしか対応していないため、
    v2用のClientとは別に用意しています。
    """
    import tweepy

    creds = _get_credentials()
    auth = tweepy.OAuth1UserHandler(
        creds["api_key"],
        creds["api_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    return tweepy.API(auth)


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


def post_tweet(text: str, image_path: str | None = None) -> bool:
    """
    1件のツイートを投稿します。
    DRY_RUN=true のときは、実際には投稿せずログに内容を表示するだけです。

    image_path を指定すると、その画像を添付して投稿します
    （ファイルが存在しない場合は、画像なしでテキストのみ投稿します）。

    戻り値は「実際にXへ投稿できたかどうか」です。
    DRY_RUNのときは常にFalseを返します。呼び出し側は、この戻り値を見て
    「投稿済み記事リスト」に記録するかどうかを判断してください
    （DRY_RUNで確認しただけの記事を、誤って投稿済み扱いにしないため）。
    """
    length = weighted_length(text)
    if length > 280:
        logger.warning(
            "投稿文がXの文字数上限を超えている可能性があります（換算%d文字）。内容を短くしてください。",
            length,
        )

    if image_path and not os.path.exists(image_path):
        logger.warning("指定された画像が見つかりません（%s）。画像なしで投稿します。", image_path)
        image_path = None

    if _is_dry_run():
        logger.info(
            "[DRY RUN] 実際には投稿していません。内容だけ表示します:\n---\n%s\n---\n添付画像: %s",
            text,
            image_path or "なし",
        )
        return False

    client = get_client()
    try:
        media_ids = None
        if image_path:
            media_api = get_media_api()
            media = media_api.media_upload(filename=image_path)
            media_ids = [media.media_id_string]

        response = client.create_tweet(text=text, media_ids=media_ids)
        logger.info("投稿しました: tweet_id=%s", response.data.get("id"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("投稿に失敗しました: %s", exc)
        raise
