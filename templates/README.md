# Dify ワークフローテンプレート - 書面審査エージェント

## 概要

企業間の契約審査業務を自動化するDifyワークフローのテンプレート集です。
ワークフロー構造（ノード接続パターン）と業務ロジック（プロンプト、ルール、スキーマ）を分離し、
新しい業務への適用を容易にしています。

## ファイル構成

```
templates/
├── business_logic/
│   └── document_review.yaml          # 業務ロジック定義（書面審査のサンプル）
├── template_orchestrator.yml          # オーケストレータ（エージェント）
├── template_check_tool.yml            # 書面チェックツール
├── template_judgment_tool.yml         # 承認・差戻し判定ツール
├── template_registration_tool.yml     # 結果登録ツール
└── README.md                          # 本ファイル
```

## テンプレート一覧

### 1. template_orchestrator.yml
**パターン: Start → Agent (ReAct) → End**

ReActエージェントが3つのツールを順番に呼び出して業務フロー全体を制御します。

### 2. template_check_tool.yml
**パターン: 正常系 + 失敗系(fail-branch) の2パス**

ファイルを取得→画像変換→LLM Visionでチェック→差戻しID判定を行います。
ファイル取得失敗時は「未添付」として処理する失敗系パスも備えています。

### 3. template_judgment_tool.yml
**パターン: Start → LLM → End**

チェック結果を受け取り、判定基準一覧と照合して承認/差戻しを判定します。
最もシンプルな構造です。

### 4. template_registration_tool.yml
**パターン: Start → ParameterExtractor → LLM → Code → HTTP POST → End**

処理結果からパラメータを抽出し、メタデータJSONを生成して外部APIに登録します。

## 使い方

### Step 1: 業務ロジックの定義

`business_logic/document_review.yaml` をコピーし、自業務用のファイルを作成します。

```bash
cp business_logic/document_review.yaml business_logic/my_business.yaml
```

以下の項目を自業務に合わせて記入してください:

| 項目 | 説明 |
|------|------|
| `input_schema` | 入力データのJSONフォーマット |
| `check_criteria` | チェック観点のリスト |
| `return_comments` | 差戻しコメント一覧 (ID: コメント文) |
| `check_items` | チェック項目一覧 (ID: 項目名) |
| `flow_type_mapping` | フロー種別マッピング |
| `extraction_parameters` | 結果登録用の抽出パラメータ |
| `external_api` | 外部APIの接続情報 |

### Step 2: テンプレートYMLのカスタマイズ

各テンプレートYMLファイル内の `# ★カスタマイズ:` コメントがある箇所を、
Step 1で作成した業務ロジックの値に差し替えます。

主なカスタマイズ箇所:

| テンプレート | カスタマイズ箇所 |
|---|---|
| オーケストレータ | ツール名、入力スキーマ、ツール実行順序、出力フォーマット |
| チェックツール | チェック観点、差戻しコメントID一覧、チェック項目ID一覧 |
| 判定ツール | 差戻しコメント一覧（判定基準） |
| 結果登録ツール | 抽出パラメータ定義、APIエンドポイント、ペイロード構造 |

### Step 3: Difyへのインポート

1. Difyの管理画面を開く
2. 「DSLをインポート」を選択
3. **ツールを先にインポート** (チェック→判定→結果登録の順)
4. 各ツールを「ツールとして公開」し、provider_name (UUID) をメモ
5. オーケストレータYMLの `provider_name` を上記UUIDに更新
6. オーケストレータをインポート

### Step 4: ツールのUUID更新（重要）

オーケストレータの `tools` セクションにある `provider_name` は
Dify環境ごとに異なるUUIDが割り当てられます。
Step 3でメモしたUUIDに更新してからインポートしてください。

```yaml
# template_orchestrator.yml 内
provider_name: 7648e6d0-5b02-4cd6-8674-fee36c65ebf5  # ★カスタマイズ: ツール公開後のUUID
```

## カスタマイズガイド

### モデル変更
すべてのテンプレートで以下の箇所を変更します:

```yaml
model:
  name: gpt-4.1-mini          # モデル名
  provider: langgenius/azure_openai/azure_openai  # プロバイダー
```

### 新しいチェック観点の追加
`template_check_tool.yml` の「発注書チェック」ノードのプロンプトに
チェック観点を追記します。対応する差戻しコメントIDとチェック項目IDも
各判定ノードに追加してください。

### 外部API変更
`template_registration_tool.yml` の HTTPリクエストノードで:
- `url`: エンドポイントURL
- `body.data[0].value`: リクエストボディJSON
- `authorization`: 認証設定

## 汎用ノードパターン

テンプレート内で変更不要な汎用パターン:

| パターン | ファイル | 説明 |
|---|---|---|
| 現在時刻取得 | registration_tool | Python: `datetime.now(ZoneInfo("Asia/Tokyo"))` |
| 結果結合 | check_tool | Python: 3つの文字列を連結 |
| fail-branch | check_tool | HTTP失敗時の分岐処理 |
| PDF→PNG | check_tool | `kalochin/pdf_process` プラグイン |
