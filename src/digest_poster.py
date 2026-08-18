"""
主要なゲームニュースサイトを横断的に調べて、その日のダイジェストページ（HTML）を
生成するスクリプト。Anthropic API（Claude）のWeb検索・Webページ取得機能を使い、
記事の選定・要約・一言コメントをAIに任せる。

出力先: docs/digest/{YYYY-MM-DD}.html
（GitHub Pagesの公開フォルダ。/docs をSourceに設定していることが前提）

このスクリプト自体はページを「生成」するだけで、Xへの投稿は行わない。
投稿は別スクリプト（digest_poster.py）が担当する。
"""

import json
import os
import re
import sys
from datetime import datetime
from html import escape as h
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIGEST_DIR = BASE_DIR / "docs" / "digest"

JST = ZoneInfo("Asia/Tokyo")

MODEL = os.getenv("DIGEST_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """\
あなたはゲーム評論同人サークル「楽脳研究所」のXアカウント運用担当です。
以下の主要なゲームニュースサイトを中心に、本日のニュースの中から
注目すべきコンシューマゲーム関連の話題を調べてください。

【対象サイト】
4Gamer.net／Game*Spark／ファミ通.com／インサイド（ゲームカテゴリのみ）
／IGN Japan／Automaton

【条件】
・コンシューマゲーム（家庭用ゲーム機、Switch/PS/Xboxなど）関連を優先する。
  PC/Steam専用の話題は、コンシューマ機にも関係する場合のみ対象にする
・フィギュア、グッズ、声優、コスプレなど、ゲーム本体と関係ない話題は除外する
・読者（レトロゲームファン〜最新ゲームファンまで幅広い）が
  関心を持ちそうな話題を5〜8件選ぶ
・レトロゲーム関連（復刻・リマスター・旧世代ハードの話題）があれば積極的に含める
・要約には、事実の羅列だけでなく「楽脳研究所らしい一言コメント」を添える
  （煽りすぎず、独自目線でひとこと、程度のトーン）

【重要・見出しのルール】
・見出し（title）は、必ずWeb取得ツールで実際に記事ページを開いて確認した
  「本当の記事タイトル」をそのまま使うこと。要約や言い換えで見出しを作らない
・記事が複数トピックをまとめた記事（新作紹介まとめ記事など）の場合も、
  実際のタイトルをそのまま使う。1トピックだけを取り出して見出しを作り変えない
・記事のOGP画像（og:imageメタタグ）のURLも、Web取得ツールで確認して含めること。
  取得できなかった場合は image_url を null にする

【重要・出力の書き方】
・summary や comment の文章には、<cite>のような引用タグや出典マークアップを
  一切含めないこと。自分の言葉で書いた、タグなしの通常の文章だけにする
・各記事の要約は簡潔にすること（summaryは2〜3文、commentは1文程度）。
  長々とした引用の貼り付けはしない

【出力形式】
必ず、以下の形式のJSON配列を ```json ... ``` のコードブロックで出力してください。
これ以外の説明文は最後の回答に含めないこと（調査の途中経過の発言は問題ない）。

```json
[
  {
    "title": "記事の実際のタイトル（そのまま）",
    "url": "記事のURL",
    "source": "出典サイト名（例: ファミ通.com）",
    "image_url": "OGP画像のURL、取得できなければnull",
    "summary": "2〜3文程度の要約",
    "comment": "楽脳研究所らしい一言コメント（1文程度）"
  }
]
```
"""


def call_claude(today_str: str) -> str:
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY環境変数を自動で読む

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 10,
            },
            {
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "max_uses": 10,
                # タイトルとog:image（どちらもページ先頭のhead部分にある）が
                # 取れれば十分なため、取得する文章量は少なめに絞る。
                # ここが大きすぎると、記事を何件も取得するうちに出力の上限
                # (max_tokens)を使い切ってしまい、肝心の要約が書けなくなる。
                "max_content_tokens": 2000,
                # 引用タグ(<cite>...)を出力に含めると、それだけで出力が
                # 大きく膨らみ、max_tokensに達して出力が途中で切れる原因になる。
                # このダイジェストでは引用表示を使わないため、オフにしておく。
                "citations": {"enabled": False},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": f"本日（{today_str}）分のゲームニュースダイジェストを作成してください。",
            }
        ],
    )

    # レスポンス中の最後のtextブロックを取り出す
    # （途中の検索過程のtextブロックではなく、最終的な結論部分を使うため）
    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        block_types = [block.type for block in response.content]
        print(
            f"[診断情報] stop_reason={response.stop_reason} "
            f"content_block_types={block_types} "
            f"usage={response.usage}"
        )
        raise RuntimeError(
            "Claudeからテキスト応答が得られませんでした"
            "（出力の上限に達した可能性があります。上の診断情報を確認してください）。"
        )
    return text_blocks[-1]


def strip_cite_tags(text: str) -> str:
    """
    <cite index="...">本文</cite> のような引用タグが万が一混ざっていた場合に、
    タグだけを取り除いて中の文章を残す（保険的な処理）。
    """
    return re.sub(r"</?cite[^>]*>", "", text)


def extract_json(text: str) -> list:
    text = strip_cite_tags(text)

    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        # コードブロックなしでJSON配列らしきものがそのまま返ってきた場合の保険
        match = re.search(r"(\[.*\])", text, re.DOTALL)
        if not match:
            raise RuntimeError(
                "応答からJSONを抽出できませんでした（出力が途中で切れている可能性があります）。"
                "応答内容:\n" + text[:2000]
            )
    return json.loads(match.group(1))


def render_html(items: list, date_obj: datetime) -> str:
    date_label = f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"

    cards_html = []
    for item in items:
        title = h(item.get("title", ""))
        url = item.get("url", "")
        source = h(item.get("source", ""))
        summary = h(item.get("summary", ""))
        comment = h(item.get("comment", ""))
        image_url = item.get("image_url")

        img_html = ""
        if image_url:
            img_html = (
                f'<img class="thumb" src="{h(image_url)}" alt="" loading="lazy" '
                f'onerror="this.style.display=\'none\'">'
            )

        cards_html.append(f"""
  <div class="card">
    <span class="source">{source}</span>
    {img_html}
    <h2><a href="{h(url)}" target="_blank" rel="noopener">{title}</a></h2>
    <p>{summary}</p>
    <p class="comment">💬 {comment}</p>
    <a class="readmore" href="{h(url)}" target="_blank" rel="noopener">元記事を読む →</a>
  </div>""")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{date_label}のゲームニュースまとめ｜楽脳研究所</title>
<style>
  :root {{
    --bg: #14151a;
