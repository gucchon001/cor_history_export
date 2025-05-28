#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
汎用ユーティリティ関数を提供するモジュール

このモジュールは、ファイル操作やデータ処理など、
プロジェクト全体で使用される汎用的な関数を提供します。
"""

import os
import glob
import time
from pathlib import Path
from typing import List, Optional, Dict, Set, Any
from datetime import datetime
import logging
import csv

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env

logger = get_logger(__name__)

def find_latest_file(directory: str, pattern: str) -> Optional[str]:
    """
    指定されたディレクトリ内で、指定されたパターンに一致する最新のファイルを探す
    
    Args:
        directory (str): 検索対象のディレクトリパス
        pattern (str): ファイル名のパターン（例: "*.csv"）
        
    Returns:
        Optional[str]: 最新のファイルのパス。ファイルが見つからない場合はNone。
    """
    if not os.path.exists(directory):
        return None
    
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    
    # 最終更新日時でソート
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def find_latest_csv_in_downloads(max_age_minutes: int = 30, retry_count: int = 3, retry_interval: int = 10) -> Optional[str]:
    """
    ダウンロードディレクトリ内で指定時間内に更新された最新のCSVファイルを探す
    
    Args:
        max_age_minutes (int): 検索するファイルの最大経過時間（分）
        retry_count (int): ファイルが見つからない場合のリトライ回数
        retry_interval (int): リトライ間隔（秒）
        
    Returns:
        Optional[str]: 最新のCSVファイルのパス。ファイルが見つからない場合はNone。
    """
    for retry in range(retry_count):
        try:
            # 現在時刻を基準に、指定分数以内のファイルを検索
            current_time = time.time()
            max_age_seconds = max_age_minutes * 60
            min_timestamp = current_time - max_age_seconds  # 30分前
            
            logger.info(f"最大{max_age_minutes}分以内に更新されたCSVファイルを検索します (試行 {retry+1}/{retry_count})")
            
            # 設定ファイルで指定されたブラウザダウンロードディレクトリを最優先で追加
            download_dirs = []
            try:
                browser_download_dir = env.get_config_value("DOWNLOAD", "BROWSER_DOWNLOAD_DIR", fallback="")
                if browser_download_dir:
                    # 引用符があれば削除
                    browser_download_dir = browser_download_dir.strip('"\'')
                    if os.path.exists(browser_download_dir):
                        logger.info(f"ブラウザのダウンロードディレクトリを追加: {browser_download_dir}")
                        # 最優先でリストに追加
                        download_dirs.append(browser_download_dir)
            except Exception as e:
                logger.warning(f"設定ファイルからブラウザダウンロードディレクトリを取得中にエラー: {str(e)}")
            
            # 設定ファイルで指定されたバックアップディレクトリを追加
            try:
                backup_dir = env.get_config_value("DOWNLOAD", "BACKUP_DIRECTORY", fallback="downloads")
                if backup_dir:
                    # 引用符があれば削除
                    backup_dir = backup_dir.strip('"\'')
                    
                    # 相対パスを絶対パスに変換
                    backup_path = Path(backup_dir)
                    if not backup_path.is_absolute():
                        backup_dir = os.path.join(env.get_project_root(), backup_dir)
                        
                    if os.path.exists(backup_dir):
                        logger.info(f"バックアップディレクトリを追加: {backup_dir}")
                        download_dirs.append(backup_dir)
            except Exception as e:
                logger.warning(f"設定ファイルからバックアップディレクトリを取得中にエラー: {str(e)}")
            
            # 既存の検索ロジックをバックアップとして残す
            # ユーザーのダウンロードディレクトリを優先的に検索
            # Windows環境の一般的なダウンロードフォルダ
            home_dir = os.path.expanduser("~")
            user_download_dirs = [
                os.path.join(home_dir, "Downloads"),
                os.path.join(home_dir, "ダウンロード")
            ]
            
            # 環境変数からダウンロードディレクトリを追加
            if "USERPROFILE" in os.environ:
                user_download_dirs.append(os.path.join(os.environ["USERPROFILE"], "Downloads"))
                user_download_dirs.append(os.path.join(os.environ["USERPROFILE"], "ダウンロード"))
            
            # OneDriveのダウンロードフォルダも確認
            if "USERPROFILE" in os.environ:
                onedrive_dir = os.path.join(os.environ["USERPROFILE"], "OneDrive")
                if os.path.exists(onedrive_dir):
                    user_download_dirs.append(os.path.join(onedrive_dir, "Downloads"))
                    user_download_dirs.append(os.path.join(onedrive_dir, "ダウンロード"))
                    
            # ユーザーのダウンロードディレクトリを追加（優先度低）
            for dir_path in user_download_dirs:
                if os.path.exists(dir_path) and dir_path not in download_dirs:
                    download_dirs.append(dir_path)
            
            # プロジェクト内のdownloadsディレクトリも確認
            project_download_dir = os.path.join(os.getcwd(), "downloads")
            if os.path.exists(project_download_dir) and project_download_dir not in download_dirs:
                download_dirs.append(project_download_dir)
            
            # 重複を排除し、存在するパスのみを保持
            unique_download_dirs = []
            for dir_path in download_dirs:
                if dir_path not in unique_download_dirs and os.path.exists(dir_path):
                    unique_download_dirs.append(dir_path)
            
            logger.info(f"検索対象ディレクトリ: {unique_download_dirs}")
            
            # 検索対象のCSVファイルを集める
            csv_candidates = []
            
            # 各ディレクトリから指定時間内に更新されたCSVファイルを探す
            for dir_path in unique_download_dirs:
                if os.path.exists(dir_path):
                    for file_name in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, file_name)
                        if (os.path.isfile(file_path) and 
                            file_name.lower().endswith('.csv') and
                            os.path.getmtime(file_path) >= min_timestamp):
                            
                            file_mod_time = os.path.getmtime(file_path)
                            time_diff_seconds = current_time - file_mod_time
                            time_diff_minutes = time_diff_seconds / 60
                            logger.info(f"候補ファイル: {file_path} (更新: {time_diff_minutes:.1f}分前)")
                            csv_candidates.append(file_path)
            
            # 該当するファイルがない場合
            if not csv_candidates:
                logger.warning(f"指定時間内({max_age_minutes}分)に更新されたCSVファイルが見つかりませんでした")
                if retry < retry_count - 1:
                    logger.info(f"{retry_interval}秒後にリトライします")
                    time.sleep(retry_interval)
                    continue
                else:
                    logger.error(f"リトライ回数({retry_count}回)を超えました。CSVファイルが見つかりませんでした。")
                    return None
            
            # 最新のファイルを返す
            if csv_candidates:
                # 更新日時でソート
                latest_file = max(csv_candidates, key=os.path.getmtime)
                file_mod_time = os.path.getmtime(latest_file)
                time_diff_seconds = current_time - file_mod_time
                time_diff_minutes = time_diff_seconds / 60
                logger.info(f"最新のCSVファイルを発見しました: {latest_file} (更新: {time_diff_minutes:.1f}分前)")
                return latest_file
                
        except Exception as e:
            logger.error(f"CSVファイルの検索中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            if retry < retry_count - 1:
                logger.info(f"{retry_interval}秒後にリトライします")
                time.sleep(retry_interval)
            else:
                logger.error(f"リトライ回数({retry_count}回)を超えました。エラーが解決しません。")
                return None
    
    return None

def wait_for_new_csv_in_downloads(timeout: int = 60, check_interval: float = 1.0) -> Optional[str]:
    """
    ダウンロードディレクトリ内に新しいCSVファイルが現れるのを待つ
    
    Args:
        timeout (int): タイムアウト時間（秒）
        check_interval (float): チェック間隔（秒）
        
    Returns:
        Optional[str]: 新しいCSVファイルのパス。タイムアウトした場合はNone。
    """
    # プロジェクト内のdownloadsディレクトリを最初に確認
    project_download_dir = os.path.join(os.getcwd(), "downloads")
    download_dirs = []
    
    if os.path.exists(project_download_dir):
        download_dirs.append(project_download_dir)
        logger.info(f"プロジェクト内のダウンロードディレクトリを監視します: {project_download_dir}")
    
    # 設定ファイルで指定されたダウンロードディレクトリを追加（優先度高）
    try:
        config_download_dir = env.get_config_value("DOWNLOAD", "DIRECTORY", fallback="")
        if config_download_dir:
            # 引用符があれば削除
            config_download_dir = config_download_dir.strip('"\'')
            if os.path.exists(config_download_dir):
                logger.info(f"設定ファイルで指定されたダウンロードディレクトリを監視します: {config_download_dir}")
                download_dirs.insert(0, config_download_dir)
    except Exception as e:
        logger.warning(f"設定ファイルからダウンロードディレクトリを取得中にエラー: {str(e)}")
    
    # ユーザーのダウンロードディレクトリも念のため確認
    home_dir = os.path.expanduser("~")
    user_download_dirs = [
        os.path.join(home_dir, "Downloads"),
        os.path.join(home_dir, "ダウンロード"),
        os.path.join(home_dir, "Desktop"),
        os.path.join(home_dir, "デスクトップ")
    ]
    
    # 環境変数からダウンロードディレクトリを追加
    for env_var in ["USERPROFILE", "HOME", "HOMEPATH"]:
        if env_var in os.environ:
            user_download_dirs.append(os.path.join(os.environ[env_var], "Downloads"))
            user_download_dirs.append(os.path.join(os.environ[env_var], "ダウンロード"))
    
    # Windowsの場合、OneDriveのダウンロードフォルダも確認
    if "USERPROFILE" in os.environ:
        onedrive_dir = os.path.join(os.environ["USERPROFILE"], "OneDrive")
        if os.path.exists(onedrive_dir):
            user_download_dirs.append(os.path.join(onedrive_dir, "Downloads"))
            user_download_dirs.append(os.path.join(onedrive_dir, "ダウンロード"))
    
    # 存在するユーザーのダウンロードディレクトリを追加
    for dir_path in user_download_dirs:
        if os.path.exists(dir_path):
            download_dirs.append(dir_path)
            logger.info(f"ユーザーのダウンロードディレクトリも監視します: {dir_path}")
    
    if not download_dirs:
        logger.error("有効なダウンロードディレクトリが見つかりませんでした")
        return None
    
    # 現在のCSVファイルとその更新時刻を記録
    current_files = {}
    for download_dir in download_dirs:
        for file_path in glob.glob(os.path.join(download_dir, "*.csv")):
            current_files[file_path] = os.path.getmtime(file_path)
            logger.debug(f"既存のCSVファイルを検出: {file_path}")
    
    logger.info(f"ダウンロード監視を開始します。既存のCSVファイル数: {len(current_files)}")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # 少し待機
        time.sleep(check_interval)
        
        # 新しいCSVファイルを探す
        for download_dir in download_dirs:
            for file_path in glob.glob(os.path.join(download_dir, "*.csv")):
                # 新しいファイルか、更新されたファイルを検出
                if file_path not in current_files or os.path.getmtime(file_path) > current_files.get(file_path, 0):
                    # ファイルサイズが0でないことを確認（ダウンロード中でない）
                    if os.path.getsize(file_path) > 0:
                        # ファイルが完全にダウンロードされるまで少し待機
                        time.sleep(2)
                        
                        # ファイルサイズが変わらなくなったことを確認（ダウンロード完了）
                        initial_size = os.path.getsize(file_path)
                        time.sleep(1)
                        if os.path.getsize(file_path) == initial_size:
                            logger.info(f"新しいCSVファイルを検出: {file_path}")
                            return file_path
    
    # タイムアウト
    logger.warning(f"タイムアウト（{timeout}秒）: 新しいCSVファイルは検出されませんでした")
    
    # タイムアウト時に最新のCSVファイルを返す（代替手段）
    latest_csv = None
    latest_time = 0
    
    # プロジェクト内のdownloadsディレクトリを優先
    if os.path.exists(project_download_dir):
        for file_path in glob.glob(os.path.join(project_download_dir, "*.csv")):
            file_time = os.path.getmtime(file_path)
            if file_time > latest_time:
                latest_time = file_time
                latest_csv = file_path
    
    # プロジェクト内で見つからない場合は他のディレクトリも確認
    if not latest_csv:
        for download_dir in download_dirs:
            if download_dir != project_download_dir:  # プロジェクトディレクトリは既に確認済み
                for file_path in glob.glob(os.path.join(download_dir, "*.csv")):
                    file_time = os.path.getmtime(file_path)
                    if file_time > latest_time:
                        latest_time = file_time
                        latest_csv = file_path
    
    if latest_csv and latest_time > start_time - 300:  # 5分以内に更新されたファイルなら使用
        logger.info(f"タイムアウトしましたが、最近更新されたCSVファイルを使用します: {latest_csv}")
        return latest_csv
    
    return None

def move_file_to_data_dir(file_path: str, new_filename: Optional[str] = None, keep_original: bool = False) -> Optional[str]:
    """
    ファイルをdataディレクトリに移動する
    
    Args:
        file_path (str): 移動するファイルのパス
        new_filename (Optional[str]): 新しいファイル名（指定しない場合は元のファイル名を使用）
        keep_original (bool): 元のファイルを保持するかどうか（デフォルトはFalse）
        
    Returns:
        Optional[str]: 移動後のファイルパス。失敗した場合はNone。
    """
    if not os.path.exists(file_path):
        logger.error(f"移動元ファイルが存在しません: {file_path}")
        return None
    
    # dataディレクトリのパスを取得
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = os.path.join(base_dir, "data")
    
    # dataディレクトリが存在しない場合は作成
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"dataディレクトリを作成しました: {data_dir}")
    
    # 新しいファイル名を設定
    if new_filename is None:
        new_filename = os.path.basename(file_path)
    
    # タイムスタンプを付与
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename, ext = os.path.splitext(new_filename)
    new_filename = f"{filename}_{timestamp}{ext}"
    
    # 移動先のパス
    dest_path = os.path.join(data_dir, new_filename)
    
    try:
        import shutil
        if keep_original:
            # ファイルをコピー
            shutil.copy2(file_path, dest_path)
            logger.info(f"ファイルをコピーしました: {file_path} -> {dest_path}")
        else:
            # ファイルを移動
            shutil.move(file_path, dest_path)
            logger.info(f"ファイルを移動しました: {file_path} -> {dest_path}")
        
        return dest_path
    except Exception as e:
        logger.error(f"ファイルの移動/コピー中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None 

def extract_csv_differences(new_file_path: str, reference_file_path: str, output_file_path: str) -> bool:
    """
    2つのCSVファイル間の差分レコードを抽出し、新しいCSVファイルに保存する
    
    Args:
        new_file_path (str): 新しくダウンロードしたCSVファイルのパス
        reference_file_path (str): 比較するリファレンスCSVファイルのパス（前回のデータ）
        output_file_path (str): 差分レコードを保存する出力ファイルのパス
        
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    try:
        if not os.path.exists(new_file_path):
            logger.error(f"新しいCSVファイルが存在しません: {new_file_path}")
            return False
            
        if not os.path.exists(reference_file_path):
            logger.warning(f"リファレンスCSVファイルが存在しません: {reference_file_path}")
            logger.info("リファレンスファイルがないため、すべてのレコードを新規として扱います")
            # リファレンスファイルがない場合は、新しいファイルをそのままコピー
            import shutil
            shutil.copy2(new_file_path, output_file_path)
            logger.info(f"新しいファイルをそのままコピーしました: {output_file_path}")
            return True
        
        # リファレンスCSVからレコードを読み込み、一意なキーでインデックス化
        reference_records = set()
        reference_header = []
        
        # CSVファイルのエンコーディングを推測
        encoding = 'utf-8'
        try:
            with open(reference_file_path, 'r', encoding=encoding) as f:
                content = f.read(1024)  # 先頭の一部を読み込む
                if '\0' in content:  # NULL文字が含まれる場合
                    encoding = 'utf-16'
                    logger.info(f"リファレンスファイルのエンコーディングをUTF-16に設定しました")
        except UnicodeDecodeError:
            # UTF-8で失敗した場合、Shift-JISを試す
            encoding = 'shift_jis'
            logger.info(f"リファレンスファイルのエンコーディングをShift-JISに設定しました")
        
        # リファレンスファイルの詳細情報をログに出力
        logger.info(f"リファレンスファイル: {reference_file_path}, エンコーディング: {encoding}")    
            
        with open(reference_file_path, 'r', encoding=encoding, errors='replace') as csv_file:
            reader = csv.reader(csv_file)
            try:
                reference_header = next(reader)  # ヘッダー行を取得
                logger.info(f"リファレンスCSVヘッダー: {', '.join(reference_header) if reference_header else '空'}")
            except StopIteration:
                logger.error(f"リファレンスCSVファイルが空です: {reference_file_path}")
                return False
                
            # 各行をタプルに変換して保存（すべての値を連結した文字列）
            for row in reader:
                reference_records.add(tuple(row))
        
        logger.info(f"リファレンスCSVから {len(reference_records)} 件のレコードを読み込みました")
        
        # 新しいCSVファイルを読み込み、差分レコードを抽出
        new_records = []
        new_header = []
        
        # 新しいCSVファイルのエンコーディングを推測
        encoding = 'utf-8'
        try:
            with open(new_file_path, 'r', encoding=encoding) as f:
                content = f.read(1024)
                if '\0' in content:
                    encoding = 'utf-16'
                    logger.info(f"新しいファイルのエンコーディングをUTF-16に設定しました")
        except UnicodeDecodeError:
            encoding = 'shift_jis'
            logger.info(f"新しいファイルのエンコーディングをShift-JISに設定しました")
        
        # 新しいファイルの詳細情報をログに出力 
        logger.info(f"新しいファイル: {new_file_path}, エンコーディング: {encoding}")
            
        with open(new_file_path, 'r', encoding=encoding, errors='replace') as csv_file:
            reader = csv.reader(csv_file)
            try:
                new_header = next(reader)  # ヘッダー行を取得
                logger.info(f"新しいCSVヘッダー: {', '.join(new_header) if new_header else '空'}")
            except StopIteration:
                logger.error(f"新しいCSVファイルが空です: {new_file_path}")
                return False
                
            # エンコーディングの違いによる比較の問題を避けるため、読み込んだ行数をカウント
            total_new_records = 0
            matched_records = 0
            
            # 差分レコードを抽出
            for row in reader:
                total_new_records += 1
                row_tuple = tuple(row)
                if row_tuple not in reference_records:
                    new_records.append(row)
                else:
                    matched_records += 1
        
        logger.info(f"新しいCSVの合計レコード数: {total_new_records}")
        logger.info(f"リファレンスCSVと一致したレコード数: {matched_records}")
        logger.info(f"新しいCSVから {len(new_records)} 件の差分レコードを抽出しました")
        
        # 差分レコードが0件の場合の処理
        if len(new_records) == 0:
            logger.warning("差分レコードが0件です。データに変更がないか、比較方法に問題がある可能性があります。")
            
            # ヘッダーのみのファイルを作成するか、元のファイルをコピーするか決定
            if total_new_records > 0:
                logger.info("新しいファイルには記録があるのに差分が0件なので、エンコーディングや比較方法に問題がある可能性があります。")
                # 問題診断のためサンプルデータを出力
                if total_new_records > 0 and len(reference_records) > 0:
                    sample_new = list(row_tuple)[:3] if total_new_records > 0 else []
                    sample_ref = list(next(iter(reference_records)))[:3] if reference_records else []
                    logger.info(f"新しいファイルのサンプル: {sample_new}")
                    logger.info(f"リファレンスファイルのサンプル: {sample_ref}")
            
            # 差分がない場合もヘッダー行のみのファイルを作成する
            logger.info("差分はありませんが、ヘッダー行のみの空ファイルを作成します")
            
            # 出力ディレクトリが存在しない場合は作成
            output_dir = os.path.dirname(output_file_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            # ヘッダー行のみのCSVファイルを保存
            with open(output_file_path, 'w', encoding='utf-8', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(new_header)  # ヘッダー行のみを書き込み
            
            logger.info(f"ヘッダー行のみの空ファイルを保存しました: {output_file_path}")
            return True
        
        # 差分レコードを新しいCSVファイルに保存
        # 出力ディレクトリが存在しない場合は作成
        output_dir = os.path.dirname(output_file_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        with open(output_file_path, 'w', encoding='utf-8', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(new_header)  # ヘッダー行を書き込み
            writer.writerows(new_records)  # 差分レコードを書き込み
        
        logger.info(f"差分レコードを出力ファイルに保存しました: {output_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"CSVファイルの差分抽出中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def find_latest_file_by_extension(directory: str, extension: str, max_age_minutes: int = None) -> Optional[str]:
    """
    指定されたディレクトリ内で、特定の拡張子を持つ最新のファイルを検索する
    
    Args:
        directory (str): 検索するディレクトリのパス
        extension (str): 検索する拡張子（例: 'csv', 'txt'）。ドットは含めない
        max_age_minutes (int, optional): 検索するファイルの最大経過時間（分）。Noneの場合は時間制限なし
        
    Returns:
        Optional[str]: 最新のファイルのパス。ファイルが見つからない場合はNone
    """
    try:
        if not os.path.exists(directory):
            logger.error(f"指定されたディレクトリが存在しません: {directory}")
            return None
            
        # ファイル拡張子にドットが含まれていない場合は追加
        if not extension.startswith('.'):
            extension = f".{extension}"
            
        # 現在時刻と時間制限（指定されている場合）
        current_time = time.time()
        time_limit_exists = max_age_minutes is not None and max_age_minutes > 0
        
        if time_limit_exists:
            max_age_seconds = max_age_minutes * 60
            min_timestamp = current_time - max_age_seconds
            logger.info(f"ディレクトリ '{directory}'内で最大{max_age_minutes}分以内に更新された{extension}ファイルを検索します")
        else:
            logger.info(f"ディレクトリ '{directory}'内のすべての{extension}ファイルから最新のものを検索します")
            
        # 指定された拡張子を持つすべてのファイルを検索
        candidates = []
        for f in os.listdir(directory):
            file_path = os.path.join(directory, f)
            
            # 指定された拡張子を持つファイルかつ、時間制限が無いか、時間制限内のファイル
            if (os.path.isfile(file_path) and f.lower().endswith(extension.lower()) and
                (not time_limit_exists or os.path.getmtime(file_path) >= min_timestamp)):
                
                file_mod_time = os.path.getmtime(file_path)
                time_diff_seconds = current_time - file_mod_time
                time_diff_minutes = time_diff_seconds / 60
                logger.info(f"候補ファイル: {file_path} (更新: {time_diff_minutes:.1f}分前)")
                candidates.append(file_path)
        
        if not candidates:
            if time_limit_exists:
                logger.warning(f"指定された拡張子 {extension} を持つファイルで指定時間内({max_age_minutes}分)に更新されたものが見つかりませんでした: {directory}")
            else:
                logger.warning(f"指定された拡張子 {extension} を持つファイルが見つかりませんでした: {directory}")
            return None
            
        # 更新日時でソート
        latest_file = max(candidates, key=os.path.getmtime)
        file_mod_time = os.path.getmtime(latest_file)
        time_diff_seconds = current_time - file_mod_time
        time_diff_minutes = time_diff_seconds / 60
        logger.info(f"最新のファイルを発見しました: {latest_file} (更新: {time_diff_minutes:.1f}分前)")
        return latest_file
        
    except Exception as e:
        logger.error(f"最新ファイルの検索中にエラーが発生しました: {str(e)}")
        return None

def count_csv_records(file_path: str) -> int:
    """
    CSVファイル内のレコード数（ヘッダー行を除く）をカウントする
    
    Args:
        file_path (str): CSVファイルのパス
        
    Returns:
        int: レコード数。エラーが発生した場合は-1を返す
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"ファイルが存在しません: {file_path}")
            return -1
            
        # CSVファイルのエンコーディングを推測
        encoding = 'utf-8'  # デフォルトはUTF-8
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read(1024)  # 先頭の一部を読み込む
                if '\0' in content:  # NULL文字が含まれる場合
                    encoding = 'utf-16'
                    logger.debug(f"ファイルのエンコーディングをUTF-16に設定しました: {file_path}")
        except UnicodeDecodeError:
            # UTF-8で失敗した場合、Shift-JISを試す
            encoding = 'shift_jis'
            logger.debug(f"ファイルのエンコーディングをShift-JISに設定しました: {file_path}")
            
        # レコード数をカウント
        with open(file_path, 'r', encoding=encoding, errors='replace') as csv_file:
            import csv
            reader = csv.reader(csv_file)
            try:
                next(reader)  # ヘッダー行をスキップ
                count = sum(1 for _ in reader)
                return count
            except StopIteration:
                # ヘッダー行しかない場合
                return 0
                
    except Exception as e:
        logger.error(f"レコード数のカウント中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return -1 
