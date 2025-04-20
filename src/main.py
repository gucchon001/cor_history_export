#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PORTERSシステムへのログイン処理と対応履歴エクスポート機能を実装するメインスクリプト

このスクリプトは、PORTERSシステムへのログイン処理と対応履歴のエクスポート機能を提供します。
処理フローの選択と引数の準備に特化し、実際の実行はPortersBrowserクラスに委譲します。
"""

import os
import sys
import time
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# プロジェクトのルートディレクトリをPYTHONPATHに追加
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.utils.environment import EnvironmentUtils as env
from src.utils.logging_config import get_logger
from src.modules.porters.browser import PortersBrowser
from src.modules.porters.operations import PortersOperations
from src.utils.slack_notifier import SlackNotifier

logger = get_logger(__name__)

# SlackNotifierのグローバルインスタンス
slack_notifier = None

def setup_environment():
    """
    実行環境のセットアップを行う
    - 必要なディレクトリの作成
    - 設定ファイルの読み込み
    - Slack通知の初期化
    """
    global slack_notifier
    
    # 必要なディレクトリの作成
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # 設定ファイルの読み込み
    try:
        # 環境変数の読み込み
        env.load_env()
        logger.info("環境変数を読み込みました")
        
        # 環境変数のロード後にSlackNotifierを初期化
        slack_notifier = SlackNotifier()
        
        return True
    except Exception as e:
        logger.error(f"設定ファイルの読み込みに失敗しました: {str(e)}")
        return False

def parse_arguments():
    """
    コマンドライン引数を解析する
    
    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(description='PORTERSシステムへのログイン処理と対応履歴のエクスポート')
    parser.add_argument('--headless', action='store_true', help='ヘッドレスモードで実行')
    parser.add_argument('--env', default='development', help='実行環境 (development または production)')
    parser.add_argument('--skip-operations', action='store_true', help='業務操作をスキップする')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        help='ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    
    return parser.parse_args()

def history_workflow(browser, login, **kwargs):
    """
    対応履歴の処理フローを実行する
    
    Args:
        browser (PortersBrowser): ブラウザオブジェクト
        login (PortersLogin): ログインオブジェクト
        **kwargs: その他のパラメータ
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    logger.info("対応履歴のエクスポート処理フローを実行します")
    operations = PortersOperations(browser)
    success = operations.execute_operations_flow()
    
    if success:
        logger.info("対応履歴のエクスポート処理フローが正常に完了しました")
    else:
        logger.error("対応履歴のエクスポート処理フローに失敗しました")
        
    return success

def main():
    """
    メイン処理
    
    対応履歴のエクスポート処理を実行します。
    
    Returns:
        int: 処理が成功した場合は0、失敗した場合は1
    """
    logger.info("=" * 70)
    logger.info("PORTERS対応履歴エクスポートツールを開始します")
    logger.info("=" * 70)
    
    # コマンドライン引数の解析
    args = parse_arguments()
    
    # 環境変数の設定
    os.environ['APP_ENV'] = args.env
    os.environ['LOG_LEVEL'] = args.log_level
    
    # 実行環境のセットアップ
    if not setup_environment():
        logger.error("環境のセットアップに失敗したため、処理を中止します")
        sys.exit(1)
    
    logger.info(f"実行環境: {args.env}")
    logger.info(f"ログレベル: {args.log_level}")
    
    # 設定ファイルのパス
    selectors_path = os.path.join(root_dir, "config", "selectors.csv")
    
    # 処理成功フラグ
    success = True
    
    # 業務操作のスキップフラグがOFFの場合、PORTERSへログインして処理実行
    if not args.skip_operations:
        # ワークフローパラメータの準備
        workflow_params = {
            'env': args.env,
        }
        
        # ワークフローセッションの実行
        success, workflow_results = PortersBrowser.execute_workflow_session(
            workflow_func=history_workflow,
            selectors_path=selectors_path,
            headless=args.headless,
            workflow_params=workflow_params
        )
    else:
        logger.info("業務操作をスキップします")
    
    # 終了処理
    if success:
        logger.info("================================================================================")
        logger.info("PORTERS対応履歴エクスポートツールを正常に終了します")
        logger.info("================================================================================")
        return 0
    else:
        logger.error("処理に失敗しました")
        logger.info("================================================================================")
        logger.info("PORTERS対応履歴エクスポートツールを異常終了します")
        logger.info("================================================================================")
        return 1
                
if __name__ == "__main__":
    sys.exit(main())
