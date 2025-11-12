# AI Browser Agent - ローカル自己拡張型ブラウザエージェント

AIがローカルファイルを実行し、ブラウザを理解・操作する自己拡張型フレームワーク

## 🎯 コンセプト

### あなたの要求に応えた設計

1. **ブラウザをAIが認識・操作** - Playwright でブラウザの DOM/UI を解析
2. **ローカルボタンシステム** - FastAPI 経由で特定タスク（ファイル）を実行
3. **自動トリガー** - 30分ごとの定期実行や条件ベース起動
4. **AI判断ループ** - タスク完了 → AI判断 → 次のボタン実行 or 新ボタン作成

### 「最大損害は口座残高」という前提

- リスク制限は `tasks.yaml` で明示的に設定
- 少額テストトレードでUI挙動を学習
- 画面変更にも自己適応（構成理解 → テスト → 学習）

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│          ユーザー / スケジューラー              │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         FastAPI (main.py)                       │
│  - /run/{task_name}    ボタン実行              │
│  - /status/{job_id}    状態確認                │
│  - /define_button      新ボタン登録            │
└────────────┬─────────────────────┬──────────────┘
             │                     │
             ▼                     ▼
    ┌────────────────┐    ┌────────────────────┐
    │  Task Runner   │    │  Job Watcher       │
    │  (非同期実行)  │    │  (完了監視)        │
    └────────┬───────┘    └─────────┬──────────┘
             │                      │
             ▼                      ▼
    ┌────────────────┐    ┌────────────────────┐
    │  tasks/*.py    │    │  AI Decider        │
    │  - scan_market │    │  (Claude API)      │
    │  - test_trade  │    │  次アクション判断  │
    │  - analyze...  │    └─────────┬──────────┘
    └────────┬───────┘              │
             │                      │
             ▼                      ▼
    ┌────────────────────────────────────────┐
    │      Browser Agent (Playwright)        │
    │  - ページ解析                          │
    │  - UI構造理解                          │
    │  - ボタン/フォーム操作                 │
    └────────────────────────────────────────┘
```

## 📦 セットアップ

### 1. 依存関係インストール

```bash
cd ai-browser-agent
pip install -r requirements.txt
playwright install chromium
```

### 2. 環境変数設定

```bash
cp .env.example .env
# .env ファイルに Anthropic API キーを設定
```

### 3. 起動

#### ターミナル1: FastAPI サーバー

```bash
python main.py
```

→ `http://127.0.0.1:8000` でAPI起動

#### ターミナル2: スケジューラー＋ウォッチャー

```bash
python scheduler.py
```

→ 自動実行 ＋ AI判断ループが開始

## 🔘 ボタン（タスク）システム

### 既存ボタンの実行

```bash
curl -X POST http://127.0.0.1:8000/run/scan_market
```

→ ジョブIDが返る → バックグラウンドで実行

### ジョブ状態確認

```bash
curl http://127.0.0.1:8000/status/{job_id}
```

### 登録済みボタン一覧

```bash
curl http://127.0.0.1:8000/buttons
```

### 新しいボタンを追加

#### 方法1: `tasks.yaml` に手動追加

```yaml
tasks:
  my_new_task:
    type: "python_module"
    module: "tasks.my_new_task:main"
    auto: false
    description: "新しいタスクの説明"
```

#### 方法2: API経由で動的追加

```bash
curl -X POST http://127.0.0.1:8000/define_button \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_new_task",
    "type": "python_module",
    "module": "tasks.my_new_task:main",
    "description": "動的に追加されたタスク"
  }'
```

## 🤖 AI判断フロー

1. **ジョブ完了検出** - `scheduler.py` の JobWatcher が監視
2. **AI呼び出し** - 完了タスク ＋ 結果 ＋ コンテキストを Claude に渡す
3. **判断結果** - AI が以下のいずれかを返す:
   - `run_button`: 既存ボタンを実行
   - `create_button`: 新しいタスクを提案
   - `wait`: 何もしない
   - `alert`: 人間の注意が必要
4. **実行** - 判断に基づいて次のアクションを自動実行

## 🌐 ブラウザエージェント機能

### ページ構造解析

```python
from browser_agent import BrowserAgent

agent = BrowserAgent(headless=False)
agent.start()
agent.navigate("https://your-trading-platform.com")

# UI構造を理解
structure = agent.analyze_page_structure()
# → ボタン、入力欄、リンクなどを自動抽出
```

### テストトレード（UI挙動学習）

```bash
curl -X POST http://127.0.0.1:8000/run/test_trade
```

→ 少額取引でUI要素を実際に操作して学習

## 🛡️ リスク管理

`tasks.yaml` の `risk_limits` セクションで制御:

```yaml
risk_limits:
  max_loss_per_day: 20000        # 1日最大損失
  max_position_size_pct: 2.0     # 1ポジション最大サイズ（全資産の%）
  test_trade_max_amount: 1000    # テストトレード上限
  allowed_trade_hours:
    start: "09:00"
    end: "15:00"
```

## 🔄 自己拡張の例

### シナリオ: 為替相関分析が必要になった

1. **AI判断**: 「USD/JPYとEUR/USDの相関を定期チェックするタスクが必要」
2. **AI提案**:
   ```json
   {
     "decision_type": "create_button",
     "new_button_spec": {
       "name": "scan_fx_correlation",
       "type": "python_module",
       "module": "tasks.scan_fx_correlation:main",
       "auto": true,
       "interval_sec": 7200
     }
   }
   ```
3. **ローカル側**: 提案を受けて `tasks/scan_fx_correlation.py` を生成
4. **次回以降**: この新ボタンが自動実行対象に

## 📊 実際のユースケース

### 長期資産管理（安全）

- 毎朝9:30に全口座をスキャン (`scan_market` + `analyze_portfolio`)
- リバランス候補を提示（AIが判断）
- 人間が承認ボタンを押して実行

### デイトレード（慎重に）

1. **環境学習フェーズ**
   - `browser_explore` で取引画面のUI構造を解析
   - `test_trade` で少額取引を複数回実行
   - UI定義を `ui_definition.json` に保存

2. **実運用フェーズ**
   - 市場条件が揃ったらAIが判断
   - リスク制限内でのみ自動執行
   - 全ログを記録

## 🚀 Claude Code からの実行

このプロジェクトは Claude Code 対応です:

```
# Claude にこう指示:
「ai-browser-agent プロジェクトで、uvicorn main:app --reload でサーバーを起動して。
 別ターミナルで python scheduler.py も実行して。」
```

→ Claude が実際にローカルでサーバー起動 ＋ スケジューラー実行可能

## 📝 次のステップ

1. ✅ 基本フレームワーク構築（完了）
2. 🔲 実際の取引所APIと連携
3. 🔲 本物のブラウザUI解析（Phantom Wallet等）
4. 🔲 少額テストトレードの実装
5. 🔲 本番運用（慎重に）

---

**重要**: このフレームワークは強力な自動化ツールです。
特に金融取引に使用する場合は、必ずリスク制限を設定し、小規模から開始してください。
