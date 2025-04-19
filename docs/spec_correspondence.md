# PORTERS 対応履歴エクスポート仕様書

## 概要
本プログラムは、PORTERSシステムから「対応履歴情報」データを取得し、CSVファイルとしてダウンロードするツールです。
ログイン認証は、IDとパスワードのみを利用し、二段階認証等の特別な方式は採用しません。
取得したCSVファイルのフォーマットやデータ変換、整形処理は行わず、ダウンロードしたデータをそのまま保存します。
対応履歴情報については、CSVファイルのダウンロードまでを行い、スプレッドシートへの転記は行いません。

## 処理フローの詳細

### 1. PORTERSへのログイン処理
- 環境変数からPORTERSのログイン情報（会社ID、ユーザー名、パスワード）を取得
- Seleniumを利用してPORTERSのログインページにアクセス
- ログイン情報を入力し、ログインボタンをクリック
- 二重ログインポップアップが表示された場合は、OKボタンをクリックして処理を継続
- ログイン成功後、ページ内容を解析して正常にログインできたことを確認
  *(既存の処理を流用)*

### 2. 対応履歴情報の取得
#### 2.1 対応履歴一覧画面への遷移
- メニューから「対応履歴」をクリック (`porters_menu.history_menu`)
- 「すべての対応履歴」をクリック (`porters_menu.all_history_list`)
- 対応履歴一覧画面が表示されることを確認

#### 2.2 (オプション) 検索条件の指定と実行
*   **注意:** このステップは特定の条件で絞り込む場合に実行します。全件エクスポートの場合はスキップします。
*   「アクションボタン」をクリック (`candidates_list.action_button`)
*   「エクスポート」をクリック (`candidates_list.export_button`)
*   「検索画面を開く」ボタンをクリック (`export_dialog.all_raw_data`)
*   検索条件を入力 (例: 「登録先」に値を入力 `export_dialog.registered_to`)
*   「検索」ボタンをクリック (`export_dialog.execute_search`)
*   検索結果が表示されることを確認

#### 2.3 対応履歴データのエクスポートとダウンロード
*   **全件エクスポートの場合:**
    *   「全てチェック」チェックボックスをクリック (`candidates_list.select_all_checkbox`)
    *   「アクションボタン」をクリック (`candidates_list.action_button`)
    *   「エクスポート」をクリック (`candidates_list.export_button`)
*   **共通フロー:**
    *   エクスポートモーダルで「企業対応履歴エクスポート」を選択 (`export_dialog.company_history_option`)
    *   「次へ」ボタンをクリック (1/3) (`export_dialog.next_button_1`)
    *   「次へ」ボタンをクリック (2/3) (`export_dialog.next_button_2`)
    *   「実行」ボタンをクリック (3/3) (`export_dialog.execute_button`)
    *   「OK」ボタンをクリック (`export_dialog.ok_button`)
    *   エクスポート処理の完了を待機 (5秒)
    *   画面上部の「エクスポート結果」通知をクリック (`export_result.result_list_button`)
        *   直接CSSセレクタを使用した代替アプローチも実装 (`#primary-notificationbar > li.p-notificationbar-item-export.p-notificationbar-item.p-notificationbar-item-status-finished`)
    *   表示されたツールチップ内のダウンロードリンクをクリック (`export_result.csv_download_link`)
        *   直接CSSセレクタ (`#pageActivity > div.p-ui-tooltip.queue-notification-tooltip > ul > li:nth-child(1) > div > ul > li:nth-child(1)`) や一般的なセレクタ (`div.p-ui-tooltip.queue-notification-tooltip a`) を使用した代替アプローチも実装
    *   指定されたダウンロードフォルダにCSVファイルが保存されることを確認

### 3. 終了処理
- PORTERSからログアウト
- ブラウザを終了
- 処理結果のサマリーをログに出力
  *(既存の処理を流用)*

## 技術的実装詳細

### セレクタ管理
- セレクタ情報は `config/selectors.csv` で一元管理
- セレクタ情報には、グループ名、要素名、セレクタタイプ、セレクタ値、説明を含む
- 動的に変わる要素に対しては、複数の検索方法（セレクタ、クラス名、テキスト内容）を実装

### ブラウザ操作
- ブラウザ操作は `PortersBrowser` クラスのメソッドを使用
- 要素のクリックは `click_element` メソッドを使用し、通常のクリックとJavaScriptクリックの両方を試行
- 動的に生成される要素に対しては、複数の検索方法（セレクタ、テキスト内容、一般的なセレクタ）を実装

### エラー処理
- 各操作ステップでエラーが発生した場合、詳細なエラーメッセージをログに記録
- スクリーンショットを保存し、エラー状況の詳細な分析を可能に
- 可能な限り代替手段を試行し、処理の継続を試みる

### ログ管理
- 詳細なロギングにより操作の追跡が可能
- 重要な操作の前後でスクリーンショットを取得し、処理の流れを視覚的に確認可能
- エラー発生時には完全なスタックトレースを記録

### フローの管理
- `execute_operations_flow`メソッドで全体の処理フローを制御
- 各ステップは個別のメソッドとして実装され、エラー発生時には適切なフィードバックを提供
- 対応履歴データのエクスポート処理は `export_history_data` メソッドで実装

## 実装済み処理フロー

1. `execute_common_history_flow`: 対応履歴関連の共通処理フロー（「対応履歴」メニュークリック）
2. `click_all_history`: 「すべての対応履歴」リンクをクリック
3. `select_all_candidates`: 「全てチェック」チェックボックスをクリック
4. `click_show_more_repeatedly`: 「もっと見る」ボタンを繰り返しクリックして、すべての対応履歴を表示
5. `export_history_data`: 対応履歴データのエクスポート処理を実行

## 実行オプション
- `--process`: 処理フローを指定
    - `candidates`: 求職者一覧のみエクスポート
    - `entryprocess`: 選考プロセス一覧のみエクスポート
    - `correspondence`: 対応履歴のみエクスポート
    - `both`: 求職者と選考プロセスを実行
    - `all`: 求職者、選考プロセス、対応履歴をすべて実行
    - `sequential`: 求職者取得後に選考プロセスも取得
- `--headless`: ブラウザを表示せずにヘッドレスモードで実行
- `--env [development|production]`: 実行環境を指定
- `--skip-operations`: 業務操作をスキップし、ログイン処理のみを実行
- `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: ログレベルを指定

## 実行方法

### コマンドライン実行
```bash
# 対応履歴のみエクスポート
python -m src.main --process correspondence

# すべてのデータをエクスポート
python -m src.main --process all
```

## 備考
- 本システムはブラウザの自動操作による対応履歴データのエクスポートを目的とします。
- システムはWindows環境での実行を前提として設計されています。

## 技術仕様
- Python 3.8以上が必要です。
- ブラウザの自動操作にはSeleniumを使用します。
- 設定ファイルは以下の種類を使用します：
  - `config/settings.ini`: URLなどの設定
  - `config/secrets.env`: PORTERSログイン情報
  - `config/selectors.csv`: ブラウザ操作に使用するHTML要素のセレクタ定義 