# PORTERSリストエクスポート

## プロジェクトの概要
このプロジェクトは、PORTERSシステムから「対応履歴情報」のデータを取得し、CSVファイルとしてエクスポートするツールです。

### 主な機能
- PORTERSシステムへの自動ログイン（二重ログイン回避機能付き）
- 対応履歴データの自動取得・CSVエクスポート

## バッチファイルの実行方法

### 開発環境用実行ファイル（run_dev.bat）
開発やテスト目的で使用します。

```bash
# 対応履歴を取得
run_dev.bat --process correspondence

# ヘッドレスモード（ブラウザを表示せず）で実行
run_dev.bat --headless
```

### 本番環境用実行ファイル（run.bat）
本番環境での定期実行用に最適化されています。対応履歴データの取得を実行します。

```bash
# 対応履歴データ処理を自動実行
run.bat
```

run.batは内部で以下のコマンドを実行しています：
```
python -m src.main --process correspondence
```

## コマンドラインパラメータの説明

### 処理フロー指定 (--process)
- `correspondence`: 対応履歴データをエクスポート（デフォルト）

### その他のオプション
- `--headless`: ブラウザを表示せずにヘッドレスモードで実行
- `--env [development|production]`: 実行環境の指定（設定ファイルの分岐用）
- `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: ログレベルの指定

## 対応履歴データエクスポート
対応履歴データは、CSVファイルとしてエクスポートされます。
エクスポート処理には以下の処理が含まれます：
- 対応履歴メニューへの遷移
- すべての対応履歴の表示
- エクスポート処理の実行
- CSVファイルのダウンロード

## システム要件
- Python 3.8以上
- インターネット接続環境
- ChromeブラウザがインストールされたWindows環境

## 設定ファイル
- `config/settings.ini`: URLなどの設定
- `config/secrets.env`: PORTERSログイン情報
- `config/selectors.csv`: ブラウザ操作に使用するHTML要素のセレクタ定義
