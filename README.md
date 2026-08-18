# 楽脳研究所 X自動投稿プログラム

同人サークル「楽脳研究所」のX（旧Twitter）アカウント向けに作った、投稿自動化プログラムです。
計画書（X運用計画書）で提案した、以下の3つの自動化を実装しています。

1. **ゲームニュース自動投稿**（`src/news_poster.py`）
   4Gamer・Game*Spark・インサイドのRSSから新着記事を取得し、リンク付きで自動投稿します。
2. **レトロゲーム記念日投稿**（`src/retro_anniversary.py`）
   `data/retro_game_releases.csv` に登録した発売日データをもとに、「今日は何の日」形式で投稿します。
3. **冬コミ（C109）カウントダウン投稿**（`src/countdown.py`）
   開催日までの残り日数、および開催期間中（3日間）の告知を自動投稿します。

すべてのスクリプトは、`DRY_RUN=true` の間は**実際には投稿せず、内容を画面に表示するだけ**です。
最初は必ずこのモードのまま動作確認してください。

---

## 1. 事前準備：X Developer Portalでのキー取得

支払い情報の登録が完了しているとのことなので、続けて以下を行ってください。

1. [developer.x.com](https://developer.x.com/) にログインし、開発者ポータルでアプリ（App）を新規作成します。
2. アプリの権限（User authentication settings）を「Read and Write」に設定します。投稿（書き込み）を行うために必須です。
3. 以下の4つの値を取得します。
   - API Key（Consumer Key）
   - API Key Secret（Consumer Secret）
   - Access Token
   - Access Token Secret
   - ※Access Token / Secretは、アプリの権限を「Read and Write」にしてから発行しないと、投稿権限のないトークンになってしまいます。権限設定後に再発行してください。

これらの値は、他人に見られると勝手に投稿されてしまう「パスワード」のようなものです。
絶対に人に教えたり、GitHubなどに公開しないでください。

---

## 2. ローカルでの動作確認（推奨：まずここから）

### 2-1. 準備

```bash
cd rakunou-x-automation
python3 -m venv .venv
source .venv/bin/activate   # Windowsの場合は .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` ファイルをテキストエディタで開き、取得したキーを貼り付けます（`DRY_RUN=true` のままにしておきます）。

### 2-2. 試しに動かしてみる

```bash
python src/news_poster.py
python src/retro_anniversary.py
python src/countdown.py
```

`DRY_RUN=true` の間は実際には投稿されず、ターミナルに「投稿予定の内容」が表示されるだけです。
表示された文章に問題がないか、必ず目で確認してください。

問題なければ、`.env` の `DRY_RUN` を `false` に変更すると、実際にXへ投稿されるようになります。
**いきなり自動実行に組み込まず、まずは手動で数回試してから次のステップに進むことを強くおすすめします。**

---

## 3. 定期実行の設定（GitHub Actions）

「できるだけ自動化に任せたい」というご希望に合わせて、GitHub Actions（GitHubの無料の定期実行機能）を使う方法を用意しています。
GitHubアカウントとPCさえあれば、自分のPCを常時起動しておく必要はありません。

### 3-1. GitHubリポジトリの作成

1. GitHubで新しいリポジトリを作成します（Private設定を推奨します）。
2. このフォルダの中身をリポジトリにpushします。

```bash
cd rakunou-x-automation
git init
git add .
git commit -m "初期セットアップ"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/リポジトリ名.git
git push -u origin main
```

`.env` ファイルは `.gitignore` で除外されているので、誤ってキーが公開される心配はありません。

### 3-2. GitHub Secretsにキーを登録

リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」から、以下を1つずつ登録します。

| Secret名 | 値の例 |
|---|---|
| `X_API_KEY` | 取得したAPI Key |
| `X_API_SECRET` | 取得したAPI Key Secret |
| `X_ACCESS_TOKEN` | 取得したAccess Token |
| `X_ACCESS_TOKEN_SECRET` | 取得したAccess Token Secret |
| `DRY_RUN` | `true`（最初はここから。動作確認できたら`false`に変更） |
| `MAX_NEWS_POSTS_PER_RUN` | `2` |
| `COUNTDOWN_START_DATE` | `2026-11-29` |
| `EVENT_DATE` | `2026-12-29` |
| `CIRCLE_SPACE` | サークル配置が決まったら記入（例：`東地区 A-12`）。決まっていなければ`未定` |

### 3-3. 動作確認

`.github/workflows/` に3つのワークフローがすでに入っています。pushすると自動的に有効になります。

- `news.yml`：ゲームニュースの自動投稿（1日2回）
- `retro_anniversary.yml`：レトロゲーム記念日の自動投稿（1日1回）
- `countdown.yml`：冬コミカウントダウンの自動投稿（1日1回）

リポジトリの「Actions」タブから、それぞれのワークフローを選んで「Run workflow」ボタンを押すと、スケジュールを待たずに手動で今すぐ実行して動作確認ができます。
`DRY_RUN=true` のうちは、実行結果のログ（「投稿予定の内容」）を確認するだけで、実際には投稿されません。

**最初の2週間は、`DRY_RUN=false`にしたあとも、実行結果を毎日チェックすることをおすすめします。**
計画書にも書いた通り、自動投稿が想定外の内容を出していないか確認する期間です。

---

## 4. カスタマイズ方法

### ニュースの取得元を変える・増やす

`src/news_poster.py` の `RSS_FEEDS` リストに、`(サイト名, RSSのURL)` を追加・削除するだけです。

### レトロゲームの記念日データを増やす

`data/retro_game_releases.csv` に行を追加します。列の意味は以下の通りです。

| 列名 | 内容 | 例 |
|---|---|---|
| month_day | 発売日（月日、MM-DD形式） | `07-15` |
| year | 発売年 | `1983` |
| title | タイトル名 | `ファミリーコンピュータ 本体` |
| platform | 機種名 | `ファミリーコンピュータ` |
| note | 一言コメント | `家庭用ゲーム機の代名詞` |

同梱のデータは12件だけのサンプルです。日付を間違えると信用に関わるので、Wikipediaやファミ通の「今日は何の日？」シリーズなど、信頼できる情報源で確認しながら増やしてください。

### 冬コミの情報を更新する

サークル配置（スペース番号）が決まったら、`.env`（またはGitHub Secrets）の `CIRCLE_SPACE` を更新してください。

---

## 5. 運用上の注意点（計画書からの抜粋）

- **費用について**：X APIは従量課金です。リンク付き投稿（ニュース自動投稿）は1件あたり約0.20ドル、リンクなし投稿（記念日・カウントダウン投稿）は1件あたり約0.015ドルが目安です（2026年8月時点、変動する可能性があります）。`MAX_NEWS_POSTS_PER_RUN` で上限を管理してください。developer.x.com の料金ページで定期的に最新情報を確認することをおすすめします。
- **手動投稿とのバランス**：この自動化はニュース・記念日・カウントダウンのみです。レビューや交流など、サークルらしさが出る投稿は手動で続けてください（計画書 第4章を参照）。
- **規約について**：自動いいね・自動フォロー・スパム的な連投は行っていませんが、実際に運用する前にX社の開発者ポリシーに一度目を通しておくと安心です。

---

## 6. トラブルシューティング

- **`以下のAPIキーが.envに設定されていません` と表示される**：`.env` ファイルが正しい場所にあるか、値が `your_...` のままになっていないか確認してください。
- **投稿が401/403エラーで失敗する**：Developer Portalのアプリ権限が「Read and Write」になっているか、Access Tokenをその設定後に再発行したか確認してください。
- **ニュースが全く投稿されない**：該当のRSSフィードが配信終了・変更されている可能性があります。`src/news_poster.py` の `RSS_FEEDS` のURLをブラウザで開いて、正しく表示されるか確認してください。
