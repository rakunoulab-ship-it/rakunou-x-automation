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
        max_tokens=8000,
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
                "max_uses": 12,
                "max_content_tokens": 6000,
                "citations": {"enabled": True},
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
        raise RuntimeError("Claudeからテキスト応答が得られませんでした。")
    return text_blocks[-1]


def extract_json(text: str) -> list:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        # コードブロックなしでJSON配列らしきものがそのまま返ってきた場合の保険
        match = re.search(r"(\[.*\])", text, re.DOTALL)
        if not match:
            raise RuntimeError(
                "応答からJSONを抽出できませんでした。応答内容:\n" + text[:2000]
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
    --card-bg: #1e2027;
    --accent: #7dd3c0;
    --accent2: #f2b880;
    --text: #eef0f3;
    --text-dim: #9aa1ad;
    --border: #2c2f38;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Hiragino Sans", "Yu Gothic", "Helvetica Neue", Arial, sans-serif;
    line-height: 1.7;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 32px 20px 64px; }}
  header {{ margin-bottom: 32px; }}
  .eyebrow {{ color: var(--accent); font-size: 13px; letter-spacing: 0.08em; font-weight: 600; }}
  h1 {{ font-size: 24px; margin: 8px 0 4px; line-height: 1.4; }}
  .subtitle {{ color: var(--text-dim); font-size: 14px; }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
  }}
  .card .source {{
    display: inline-block; font-size: 12px; color: var(--accent2);
    border: 1px solid var(--accent2); border-radius: 999px;
    padding: 2px 10px; margin-bottom: 10px;
  }}
  .card .thumb {{
    display: block; width: 100%; max-height: 320px; object-fit: cover;
    border-radius: 8px; margin: 0 0 14px; background: #0d0e11;
  }}
  .card h2 {{ font-size: 17px; margin: 0 0 10px; line-height: 1.5; }}
  .card h2 a {{ color: var(--text); text-decoration: none; }}
  .card h2 a:hover {{ color: var(--accent); }}
  .card p {{ margin: 0 0 12px; font-size: 14px; color: #cfd3da; }}
  .comment {{
    font-size: 13px; color: var(--accent); border-left: 3px solid var(--accent);
    padding-left: 10px; margin: 0;
  }}
  .card a.readmore {{ display: inline-block; margin-top: 12px; font-size: 13px; color: var(--text-dim); }}
  footer {{
    margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border);
    font-size: 12px; color: var(--text-dim);
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">楽脳研究所 ゲームニュースまとめ</div>
    <h1>{date_label}のゲームニュースまとめ</h1>
    <div class="subtitle">レトロハードから最新機種まで、今日気になったニュースを{len(items)}本ピックアップ</div>
  </header>
{"".join(cards_html)}
  <footer>
    楽脳研究所｜コンシューマゲーム評論同人サークル<br>
    このページはAIによる自動生成です。掲載内容は各出典サイトの記事を要約したものです。
  </footer>
</div>
</body>
</html>
"""


def main():
    now_jst = datetime.now(JST)
    today_str = f"{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    raw_text = call_claude(today_str)
    items = extract_json(raw_text)

    if not items:
        print("記事が0件でした。ページは生成しません。")
        sys.exit(1)

    html = render_html(items, now_jst)

    DOCS_DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOCS_DIGEST_DIR / f"{now_jst.strftime('%Y-%m-%d')}.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"ダイジェストページを生成しました: {output_path}（{len(items)}件）")


if __name__ == "__main__":
    main()
