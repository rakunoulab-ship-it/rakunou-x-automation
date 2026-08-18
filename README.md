# 楽脳研究所 X自動投稿プログラム

同人サークル「楽脳研究所」のX（旧Twitter）アカウント向けに作った、投稿自動化プログラムです。

現在は以下の2つの自動化を実装しています。

1. **ゲームニュース ダイジェスト投稿**（`src/digest_generator.py` + `src/digest_poster.py`）
   Anthropic API（Claude）のWeb検索・Webページ取得機能を使い、4Gamer・Game*Spark・ファミ通.com・インサイド・IGN Japan・Automatonなど主要サイトを横断的に調査。その日のコンシューマゲーム関連ニュースをAIが5〜8件選び、要約と「楽脳研究所らしい一言コメント」を添えたまとめページ（GitHub Pages上のHTML）を生成します。夜に、そのページへのリンクを1件だけXに投稿します。
   - 19:00 JST：`digest_generate.yml` がページを生成し、`docs/digest/` にコミット
   - 20:00 JST：`digest_post.yml` がそのページへのリンクをXに投稿
2. **レトロゲーム記念日投稿**（`src/retro_anniversary.py`）
   `data/retro_game_releases.csv` に登録した発売日データをもとに、「今日は何の日」形式で投稿します（毎日9:30 JST）。

以前あったRSSフィードの機械的な自動投稿（`news_poster.py`）や、冬コミカウントダウン投稿（`countdown.py`）は廃止しました。

すべてのスクリプトは、`DRY_RUN=true` の間は**実際には投稿せず、内容を画面に表示するだけ**です。
新しい変更を試すときは、必ず一度このモードで動作確認してください。

---

## 1. 事前準備：キーの取得

### 1-1. X Developer Portal

1. [developer.x.com](https://developer.x.com/) にログインし、開発者ポータルでアプリ（App）を新規作成します。
2. アプリの権限（User authentication settings）を「Read and Write」に設定します。投稿（書き込み）を行うために必須です。
3. 以下の4つの値を取得します。
   - API Key（Consumer Key）
   - API Key Secret（Consumer Secret）
   - Access Token
   - Access Token Secret
   - ※Access Token / Secretは、アプリの権限を「Read and Write」にしてから発行しないと、投稿権限のないトークンになってしまいます。権限設定後に再発行してください。
4. 支払い情報（Billing）を登録し、必要な分だけAPIクレジットを追加してください（X APIは従量課金です）。

### 1-2. Anthropic API（ダイジェスト生成用）

1. [console.anthropic.com](https://console.anthropic.com/) にログインし、Billingで少額のクレジットを追加します。
2. 「API Keys」→「Create Key」でキーを発行します（`sk-ant-...` で始まる文字列。表示は一度きりなのですぐコピーしてください）。

これらの値は、他人に見られると勝手に投稿されたり、お金を使われたりする「パスワード」のようなものです。
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
python src/digest_generator.py     # docs/digest/ に今日のダイジェストページを生成
python src/digest_poster.py        # 生成済みページへのリンクを投稿（DRY_RUN=trueなら表示のみ）
python src/retro_anniversary.py
```

`DRY_RUN=true` の間は実際には投稿されず、ターミナルに「投稿予定の内容」が表示されるだけです。
表示された文章に問題がないか、必ず目で確認してください。

問題なければ、`.env` の `DRY_RUN` を `false` に変更すると、実際にXへ投稿されるようになります。
**いきなり自動実行に組み込まず、まずは手動で数回試してから次のステップに進むことを強くおすすめします。**

---

## 3. 定期実行の設定（GitHub Actions + GitHub Pages）

「できるだけ自動化に任せたい」というご希望に合わせて、GitHub Actions（GitHubの無料の定期実行機能）を使う方法を用意しています。
GitHubアカウントさえあれば、自分のPCを常時起動しておく必要はありません。

### 3-1. GitHubリポジトリの作成

1. GitHubで新しいリポジトリを作成します。
   - ※GitHub Pages（ダイジェストページの公開）を無料プランで使うには、リポジトリを **Public** にする必要があります。実際のキー類はGitHub Secretsで管理されるので、リポジトリをPublicにしても安全性には影響しません。
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

### 3-2. GitHub Pagesを有効化

リポジトリの「Settings」→「Pages」で、Source を `main` ブランチ・`/docs` フォルダに設定します。
数分後、`https://あなたのユーザー名.github.io/リポジトリ名/` でページが公開されます。

### 3-3. GitHub SecretsとVariablesにキーを登録

リポジトリの「Settings」→「Secrets and variables」→「Actions」から登録します。

**Secrets**（「New repository secret」、値が常にログでマスクされます）

| Secret名 | 値の例 |
|---|---|
| `X_API_KEY` | 取得したAPI Key |
| `X_API_SECRET` | 取得したAPI Key Secret |
| `X_ACCESS_TOKEN` | 取得したAccess Token |
| `X_ACCESS_TOKEN_SECRET` | 取得したAccess Token Secret |
| `ANTHROPIC_API_KEY` | 取得したAnthropic APIキー（`sk-ant-...`） |

**Variables**（「Variables」タブ→「New repository variable」、機密性のない設定値）

| Variable名 | 値の例 |
|---|---|
| `DRY_RUN` | `true`（最初はここから。動作確認できたら`false`に変更） |

### 3-4. 動作確認

`.github/workflows/` に以下のワークフローが入っています。pushすると自動的に有効になります。

- `digest_generate.yml`：ゲームニュースダイジェストページの生成（19:00 JST）
- `digest_post.yml`：生成済みページへのリンク投稿（20:00 JST）
- `retro_anniversary.yml`：レトロゲーム記念日の自動投稿（9:30 JST）

リポジトリの「Actions」タブから、それぞれのワークフローを選んで「Run workflow」ボタンを押すと、スケジュールを待たずに手動で今すぐ実行して動作確認ができます。
`DRY_RUN=true` のうちは、実行結果のログ（「投稿予定の内容」）を確認するだけで、実際には投稿されません。

**最初の2週間は、`DRY_RUN=false`にしたあとも、実行結果と生成されたページの内容を毎日チェックすることをおすすめします。**
計画書にも書いた通り、自動投稿が想定外の内容を出していないか確認する期間です。

---

## 4. カスタマイズ方法

### ダイジェストの調査対象サイトや選定条件を変える

`src/digest_generator.py` の `SYSTEM_PROMPT` を編集します。対象サイトの追加・除外、除外したいジャンル（フィギュア・グッズ等）、選定件数などをここで調整できます。

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

---

## 5. 運用上の注意点（計画書からの抜粋）

- **費用について**：
  - X APIは従量課金です。リンク付き投稿（ダイジェストのリンク投稿）は1件あたり約0.20ドル、リンクなし投稿（記念日投稿）は1件あたり約0.015ドルが目安です。
  - Anthropic APIも従量課金です。ダイジェスト生成1回あたり、Web検索・ページ取得を含めておおよそ1ドル前後（内容やヒット件数により変動）。
  - 1日1回ずつの実行であれば、月あたり合計20〜40ドル程度に収まる見込みです。developer.x.com / console.anthropic.com それぞれの料金ページで定期的に最新情報を確認することをおすすめします。
- **手動投稿とのバランス**：この自動化はニュースダイジェストと記念日投稿のみです。レビューや交流など、サークルらしさが出る投稿は手動で続けてください（計画書 第4章を参照）。
- **規約について**：自動いいね・自動フォロー・スパム的な連投は行っていませんが、実際に運用する前にX社の開発者ポリシーに一度目を通しておくと安心です。

---

## 6. トラブルシューティング

- **`Could not resolve authentication method` と表示される**：`ANTHROPIC_API_KEY` がGitHub Secretsに正しく登録されているか確認してください。
- **`ModuleNotFoundError` が出る**：`requirements.txt` に必要なパッケージ（`anthropic`、`requests` など）が入っているか確認してください。
- **投稿が401/403エラーで失敗する**：Developer Portalのアプリ権限が「Read and Write」になっているか、Access Tokenをその設定後に再発行したか確認してください。
- **投稿が402エラーで失敗する**：X Developer PortalのBillingページで、APIクレジットの残高が0になっていないか確認してください。
- **ダイジェストページが投稿されない（スキップされる）**：19時の生成ワークフローが失敗しているか、GitHub Pagesの反映が遅れている可能性があります。`digest_generate.yml` の実行ログと、`https://あなたのユーザー名.github.io/リポジトリ名/digest/YYYY-MM-DD.html` が実際に開けるか確認してください。
