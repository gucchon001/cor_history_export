import os
import csv
import time
import configparser
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils.logging_config import get_logger
from src.utils.environment import EnvironmentUtils as env
from src.utils.slack_notifier import SlackNotifier

logger = get_logger(__name__)

class PortersBrowser:
    """
    ブラウザ操作を管理するクラス
    
    このクラスは、Seleniumを使用したブラウザ操作の基本機能を提供します。
    WebDriverの初期化、セレクタの読み込み、要素の取得、スクリーンショットの保存などの
    汎用的なブラウザ操作機能を担当します。また、設定ファイル（settings.ini）から
    ブラウザ関連の設定を読み込む機能も提供します。
    """
    
    def __init__(self, selectors_path=None, headless=None, timeout=10):
        """
        ブラウザ操作クラスの初期化
        
        Args:
            selectors_path (str): セレクタ情報を含むCSVファイルのパス
            headless (bool): ヘッドレスモードで実行するかどうか（Noneの場合はsettings.iniから読み込む）
            timeout (int): 要素を待機する最大時間（秒）
        """
        self.driver = None
        self.wait = None
        self.timeout = timeout
        
        # Slack通知用のインスタンスを初期化
        self.slack = SlackNotifier()
        
        # settings.iniからheadlessモードの設定を読み込む（引数で指定がなければ）
        if headless is None:
            self.headless = self._get_headless_setting()
        else:
            self.headless = headless
            
        self.selectors_path = selectors_path
        self.selectors = {}
        
        # スクリーンショット保存ディレクトリ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_dir = os.path.join("logs", "screenshots", timestamp)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # セレクタファイルが指定されている場合は読み込む
        if selectors_path and os.path.exists(selectors_path):
            self._load_selectors()
            
        # セレクタのフォールバック設定
        self._setup_fallback_selectors()
    
    def _get_headless_setting(self):
        """
        settings.iniファイルからheadlessモードの設定を読み込む
        
        Returns:
            bool: headlessモードが有効な場合はTrue、無効な場合はFalse
        """
        try:
            # 環境変数からAPP_ENVを取得
            app_env = env.get_environment()
            
            # BROWSER セクションからheadless設定を読み込む
            headless = env.get_config_value("BROWSER", "headless", default="false")
            
            # 文字列をブール値に変換
            if isinstance(headless, str):
                return headless.lower() == "true"
            return bool(headless)
            
        except Exception as e:
            logger.warning(f"settings.iniからheadless設定を読み込めませんでした: {str(e)}")
            return False
            
    def _update_headless_setting(self, headless_value):
        """
        settings.iniファイルのheadless設定を更新する
        
        Args:
            headless_value (bool): 新しいheadless設定値
            
        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            config_path = env.get_config_file()
            config = configparser.ConfigParser()
            
            # 設定ファイルを読み込む
            config.read(config_path, encoding='utf-8')
            
            # BROWSERセクションがなければ作成
            if not config.has_section("BROWSER"):
                config.add_section("BROWSER")
            
            # headless設定を更新
            config.set("BROWSER", "headless", str(headless_value).lower())
            
            # 設定を保存
            with open(config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
                
            logger.info(f"headless設定を更新しました: {headless_value}")
            return True
            
        except Exception as e:
            logger.error(f"headless設定の更新に失敗しました: {str(e)}")
            return False
    
    def _setup_fallback_selectors(self):
        """セレクタのフォールバック設定"""
        # portersグループがなければ初期化
        if not self.selectors or 'porters' not in self.selectors:
            logger.warning("PORTERSのセレクタ情報が見つかりません。デフォルト値を使用します。")
            self.selectors['porters'] = {
                'company_id': {
                    'selector_type': 'css',
                    'selector_value': "#Model_LoginForm_company_login_id"
                },
                'username': {
                    'selector_type': 'css',
                    'selector_value': "#Model_LoginForm_username"
                },
                'password': {
                    'selector_type': 'css',
                    'selector_value': "#Model_LoginForm_password"
                },
                'login_button': {
                    'selector_type': 'css',
                    'selector_value': "button[type='submit']"
                }
            }
        
        # porters_menuグループがなければ初期化
        if 'porters_menu' not in self.selectors:
            logger.warning("PORTERSメニューのセレクタ情報が見つかりません。デフォルト値を使用します。")
            self.selectors['porters_menu'] = {
                'logout_button': {
                    'selector_type': 'css',
                    'selector_value': "a[href*='logout']"
                },
                'search_button': {
                    'selector_type': 'css',
                    'selector_value': "#main > div > main > section.original-search > header > div.others > button"
                },
                'candidate_list': {
                    'selector_type': 'css',
                    'selector_value': "a[href*='candidate/list']"
                },
                'process_list': {
                    'selector_type': 'css',
                    'selector_value': "a[href*='process/list']"
                },
                'csv_download': {
                    'selector_type': 'css',
                    'selector_value': "button.csv-download"
                }
            }
    
    def setup(self):
        """
        WebDriverをセットアップする
        
        Returns:
            bool: セットアップが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("WebDriverのセットアップを開始します")
            
            # ヘッドレスモードの設定
            chrome_options = webdriver.ChromeOptions()
            
            if self.headless:
                logger.info("ヘッドレスモードで実行します")
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')
            else:
                logger.info("ブラウザ表示モードで実行します")
            
            # UAの設定
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # その他のオプション
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--lang=ja')
            
            # ブラウザウィンドウのクラッシュを防止
            chrome_options.add_argument('--disable-features=RendererCodeIntegrity')
            
            # 通知を無効化
            chrome_options.add_argument('--disable-notifications')
            
            # ChromeDriverを最新の互換性のあるバージョンに自動更新
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
            
            # ダウンロード設定
            download_dir = os.path.join(os.getcwd(), "downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # WebDriverの初期化 (ChromeDriverManagerを使用)
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            logger.info("✅ WebDriverのセットアップが完了しました")
            return True
            
        except Exception as e:
            error_message = "WebDriverのセットアップ中にエラーが発生しました"
            self._notify_error(error_message, e, {"設定": f"headless={self.headless}, timeout={self.timeout}"})
            return False
    
    def _load_selectors(self):
        """
        CSVファイルからセレクタ情報を読み込む
        
        Returns:
            bool: 読み込みが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info(f"セレクタファイルを読み込みます: {self.selectors_path}")
            
            with open(self.selectors_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'group' in row and 'name' in row and 'selector_type' in row and 'selector_value' in row:
                        group = row['group']
                        name = row['name']
                        
                        if group not in self.selectors:
                            self.selectors[group] = {}
                        
                        self.selectors[group][name] = {
                            'selector_type': row['selector_type'],
                            'selector_value': row['selector_value']
                        }
            
            logger.info(f"セレクタ情報を読み込みました: {len(self.selectors)} グループ")
            for group, selectors in self.selectors.items():
                logger.info(f"  - {group}: {len(selectors)} セレクタ")
            
            return True
            
        except Exception as e:
            logger.error(f"セレクタファイルの読み込み中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def navigate_to(self, url):
        """
        指定されたURLに移動する
        
        Args:
            url (str): 移動先のURL
            
        Returns:
            bool: 移動が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info(f"URLに移動します: {url}")
            self.driver.get(url)
            return True
        except Exception as e:
            logger.error(f"URL移動中にエラーが発生しました: {str(e)}")
            return False
    
    def get_element(self, group, name, wait_time=None):
        """
        指定されたセレクタに一致する要素を取得する
        
        Args:
            group (str): セレクタのグループ名
            name (str): セレクタの名前
            wait_time (int, optional): 要素を待機する時間（秒）。指定がない場合はデフォルトのタイムアウトを使用
            
        Returns:
            WebElement: 見つかった要素。見つからない場合はNone
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return None
        
        if group not in self.selectors or name not in self.selectors[group]:
            logger.error(f"セレクタが見つかりません: {group}.{name}")
            return None
        
        selector_info = self.selectors[group][name]
        selector_type = selector_info['selector_type']
        selector_value = selector_info['selector_value']
        
        try:
            wait = WebDriverWait(self.driver, wait_time or self.timeout)
            
            if selector_type.lower() == 'css':
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_value)))
            elif selector_type.lower() == 'xpath':
                element = wait.until(EC.presence_of_element_located((By.XPATH, selector_value)))
            elif selector_type.lower() == 'id':
                element = wait.until(EC.presence_of_element_located((By.ID, selector_value)))
            elif selector_type.lower() == 'name':
                element = wait.until(EC.presence_of_element_located((By.NAME, selector_value)))
            elif selector_type.lower() == 'class':
                element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, selector_value)))
            else:
                logger.error(f"未対応のセレクタタイプです: {selector_type}")
                return None
            
            return element
            
        except TimeoutException:
            logger.warning(f"要素が見つかりませんでした: {group}.{name} ({selector_type}: {selector_value})")
            return None
        except Exception as e:
            logger.error(f"要素の取得中にエラーが発生しました: {str(e)}")
            return None
    
    def save_screenshot(self, filename):
        """
        スクリーンショットを保存する
        
        Args:
            filename (str): 保存するファイル名
            
        Returns:
            bool: 保存が成功した場合はTrue、失敗した場合はFalse
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return False
        
        try:
            filepath = os.path.join(self.screenshot_dir, filename)
            self.driver.save_screenshot(filepath)
            logger.debug(f"スクリーンショットを保存しました: {filepath}")
            return True
        except Exception as e:
            logger.error(f"スクリーンショットの保存中にエラーが発生しました: {str(e)}")
            return False
    
    def analyze_page_content(self, html_content):
        """
        ページのHTML内容を解析する
        
        Args:
            html_content (str): 解析するHTML内容
            
        Returns:
            dict: 解析結果を含む辞書
        """
        result = {
            'page_title': '',
            'main_heading': '',
            'error_messages': [],
            'menu_items': []
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # タイトルを取得
            title_tag = soup.find('title')
            if title_tag:
                result['page_title'] = title_tag.text.strip()
            
            # 主な見出しを取得
            h1_tags = soup.find_all('h1')
            if h1_tags:
                result['main_heading'] = h1_tags[0].text.strip()
            
            # エラーメッセージを探す
            error_elements = soup.find_all(class_=lambda c: c and ('error' in c.lower() or 'alert' in c.lower()))
            for error in error_elements:
                error_text = error.text.strip()
                if error_text:
                    result['error_messages'].append(error_text)
            
            # メニュー項目を探す
            menu_elements = soup.find_all(['a', 'button'], class_=lambda c: c and ('menu' in c.lower() or 'nav' in c.lower()))
            for menu in menu_elements:
                menu_text = menu.text.strip()
                if menu_text:
                    result['menu_items'].append(menu_text)
            
            # 一般的なナビゲーション要素も探す
            nav_elements = soup.find_all('nav')
            for nav in nav_elements:
                links = nav.find_all('a')
                for link in links:
                    link_text = link.text.strip()
                    if link_text and link_text not in result['menu_items']:
                        result['menu_items'].append(link_text)
            
            return result
            
        except Exception as e:
            logger.error(f"ページ内容の解析中にエラーが発生しました: {str(e)}")
            return result
    
    def click_element(self, group, name, use_javascript=False, wait_time=None):
        """
        指定された要素をクリックする
        
        Args:
            group (str): セレクタのグループ名
            name (str): セレクタの名前
            use_javascript (bool): JavaScriptを使用してクリックするかどうか
            wait_time (int, optional): 要素を待機する時間（秒）
            
        Returns:
            bool: クリックが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            element = self.get_element(group, name, wait_time)
            if not element:
                logger.error(f"クリック対象の要素が見つかりません: {group}.{name}")
                return False
            
            # 要素が画面内に表示されるようにスクロール
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(1)  # スクロール完了を待機
            
            # クリック実行
            if use_javascript:
                logger.info(f"JavaScriptを使用して要素をクリックします: {group}.{name}")
                self.driver.execute_script("arguments[0].click();", element)
            else:
                logger.info(f"要素をクリックします: {group}.{name}")
                element.click()
            
            logger.info(f"✓ 要素のクリックに成功しました: {group}.{name}")
            return True
            
        except Exception as e:
            logger.error(f"要素のクリック中にエラーが発生しました: {group}.{name}, エラー: {str(e)}")
            self.save_screenshot(f"click_error_{group}_{name}.png")
            
            # JavaScriptでのクリックを試行（通常のクリックが失敗した場合）
            if not use_javascript:
                try:
                    logger.info(f"通常のクリックが失敗したため、JavaScriptでクリックを試みます: {group}.{name}")
                    element = self.get_element(group, name, wait_time)
                    if element:
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.info(f"✓ JavaScriptを使用した要素のクリックに成功しました: {group}.{name}")
                        return True
                except Exception as js_e:
                    logger.error(f"JavaScriptを使用した要素のクリックにも失敗しました: {str(js_e)}")
            
            return False
    
    def switch_to_new_window(self, current_handles=None, timeout=10, retries=3):
        """
        新しく開いたウィンドウに切り替える
        
        Args:
            current_handles (list, optional): 切り替え前のウィンドウハンドルリスト
            timeout (int, optional): 新しいウィンドウが開くまで待機する時間(秒)
            retries (int, optional): 失敗時のリトライ回数
            
        Returns:
            bool: 切り替えが成功した場合はTrue、失敗した場合はFalse
        """
        if not self.driver:
            logger.error("WebDriverが初期化されていません")
            return False
            
        # 現在のウィンドウハンドルが指定されていない場合は取得
        if current_handles is None:
            try:
                current_handles = self.driver.window_handles
                logger.info(f"現在のウィンドウハンドル: {current_handles}")
            except Exception as e:
                logger.error(f"現在のウィンドウハンドルの取得に失敗しました: {str(e)}")
                return False
        
        retry_count = 0
        while retry_count < retries:
            try:
                # 新しいウィンドウが開くまで待機
                start_time = time.time()
                new_handle = None
                
                while time.time() - start_time < timeout:
                    try:
                        # 現在のハンドルを再取得（セッションが無効になっていないか確認）
                        handles = self.driver.window_handles
                        
                        # 新しいウィンドウを探す
                        for handle in handles:
                            if handle not in current_handles:
                                new_handle = handle
                                break
                        
                        if new_handle:
                            break
                            
                        time.sleep(0.5)  # 短い間隔で再試行
                    except Exception as inner_e:
                        logger.warning(f"ウィンドウハンドルの取得中にエラーが発生しました（リトライ中）: {str(inner_e)}")
                        time.sleep(1)
                        continue
                
                if not new_handle:
                    logger.warning(f"新しいウィンドウが見つかりませんでした（{timeout}秒待機後）")
                    # スクリーンショットを撮影してエラーを記録
                    self.save_screenshot(f"window_switch_timeout_{retry_count}.png")
                    retry_count += 1
                    time.sleep(1)  # リトライ前に待機
                    continue
                
                # 新しいウィンドウに切り替え
                self.driver.switch_to.window(new_handle)
                
                # 切り替え後のURLを表示
                logger.info(f"新しいウィンドウに切り替えました: {self.driver.current_url}")
                
                # 切り替え後のスクリーンショット
                self.save_screenshot("after_window_switch.png")
                
                return True
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"新しいウィンドウへの切り替え中にエラーが発生しました (リトライ {retry_count}/{retries}): {str(e)}")
                
                if retry_count >= retries:
                    logger.error(f"新しいウィンドウへの切り替えに失敗しました（{retries}回リトライ後）")
                    self.save_screenshot("window_switch_error.png")
                    return False
                
                # リトライ前に待機
                time.sleep(2)
        
        return False
    
    def quit(self, error_message=None, exception=None, context=None):
        """
        WebDriverを終了する
        
        Args:
            error_message (str, optional): 通知するエラーメッセージ
            exception (Exception, optional): 例外オブジェクト
            context (dict, optional): エラーコンテキスト情報
        """
        if error_message:
            self._notify_error(error_message, exception, context)
            
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriverを正常に終了しました")
            except Exception as e:
                logger.warning(f"WebDriver終了時にエラーが発生しました: {str(e)}")
            finally:
                self.driver = None
        
    @classmethod
    def login_to_porters(cls, selectors_path=None, headless=None):
        """
        PORTERSシステムへのログイン処理を実行する
        
        Args:
            selectors_path (str): セレクタ情報を含むCSVファイルのパス
            headless (bool): ヘッドレスモードで実行するかどうか (Noneの場合はsettings.iniから読み込む)
        
        Returns:
            tuple: (success, browser, login) 処理成功の場合はTrue、失敗した場合はFalse、およびブラウザとログインオブジェクト
        """
        from src.modules.porters.login import PortersLogin
        
        try:
            logger.info("=== PORTERSシステムへのログイン処理を開始します ===")
            
            # ブラウザセットアップ
            browser = cls(selectors_path=selectors_path, headless=headless)
            
            # WebDriverのセットアップ
            if not browser.setup():
                logger.error("ブラウザのセットアップに失敗しました")
                return False, None, None
            
            # ログイン処理
            login = PortersLogin(browser)
            if not login.execute():
                logger.error("ログイン処理に失敗しました")
                # Slack通知
                browser._notify_error(
                    "PORTERSへのログイン処理に失敗しました", 
                    context={"ヘッドレスモード": str(headless), "セレクタパス": str(selectors_path)}
                )
                browser.quit()
                return False, None, None
            
            # ログイン成功後の検証
            logger.info("ログイン後の画面を検証します")
            browser.save_screenshot("login_success_verification.png")
            
            logger.info("✅ PORTERSシステムへのログイン処理が正常に完了しました")
            return True, browser, login
            
        except Exception as e:
            error_message = "PORTERSシステムへのログイン処理中にエラーが発生しました"
            logger.error(f"{error_message}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # インスタンスが作成されていればSlack通知
            if 'browser' in locals() and browser:
                browser._notify_error(
                    error_message, 
                    exception=e, 
                    context={"ヘッドレスモード": str(headless), "セレクタパス": str(selectors_path)}
                )
                browser.quit()
            else:
                # インスタンスがなければ一時的なSlackNotifierを作成して通知
                slack = SlackNotifier()
                slack.send_error(
                    error_message=error_message,
                    exception=e,
                    title="PORTERSログインエラー",
                    context={"ヘッドレスモード": str(headless), "セレクタパス": str(selectors_path)}
                )
            
            return False, None, None
    
    def set_headless_mode(self, headless_mode):
        """
        ヘッドレスモード設定を変更し、settings.iniファイルも更新する
        
        Args:
            headless_mode (bool): 新しいヘッドレスモード設定
            
        Returns:
            bool: 設定変更が成功した場合はTrue、失敗した場合はFalse
            
        Note:
            既に初期化済みのWebDriverには影響しません。
            次回のWebDriver初期化時から有効になります。
        """
        try:
            # 内部の設定を更新
            self.headless = bool(headless_mode)
            
            # settings.iniファイルも更新
            result = self._update_headless_setting(headless_mode)
            
            logger.info(f"ヘッドレスモード設定を {headless_mode} に変更しました")
            return result
        except Exception as e:
            logger.error(f"ヘッドレスモード設定の変更中にエラーが発生しました: {str(e)}")
            return False
    
    def _notify_error(self, error_message, exception=None, context=None):
        """
        エラーが発生した際にログに記録し、Slackに通知する
        
        Args:
            error_message (str): エラーメッセージ
            exception (Exception, optional): 発生した例外
            context (dict, optional): エラーのコンテキスト情報
        
        Returns:
            bool: 通知が成功した場合はTrue、失敗した場合はFalse
        """
        # エラーをログに記録
        if exception:
            logger.error(f"{error_message}: {str(exception)}")
            import traceback
            logger.error(traceback.format_exc())
        else:
            logger.error(error_message)
        
        # スクリーンショットを撮影
        screenshot_path = None
        if self.driver:
            error_screenshot = f"error_{datetime.now().strftime('%H%M%S')}.png"
            if self.save_screenshot(error_screenshot):
                screenshot_path = os.path.join(self.screenshot_dir, error_screenshot)
        
        # コンテキスト情報を準備
        ctx = context or {}
        if screenshot_path:
            ctx["スクリーンショット"] = f"保存済み: {screenshot_path}"
        
        # 現在のURLを追加
        if self.driver:
            try:
                ctx["現在のURL"] = self.driver.current_url
            except:
                ctx["現在のURL"] = "取得できません"
        
        # Slackに通知
        return self.slack.send_error(
            error_message=error_message,
            exception=exception,
            title="PORTERSブラウザ操作エラー",
            context=ctx
        )
    
    @classmethod
    def execute_workflow_session(cls, workflow_func, selectors_path=None, headless=None, workflow_params=None):
        """
        PORTERSシステムに接続し、指定されたワークフローを実行し、適切にログアウトする一連のセッションを管理する
        
        Args:
            workflow_func (callable): 実行するワークフロー関数。browser, loginオブジェクトを引数として受け取り、
                                     成功時にはTrueを、失敗時にはFalseを返す必要がある
            selectors_path (str): セレクタ情報を含むCSVファイルのパス
            headless (bool): ヘッドレスモードで実行するかどうか (Noneの場合はsettings.iniから読み込む)
            workflow_params (dict): ワークフロー関数に渡す追加パラメータ
        
        Returns:
            tuple: (success, results) セッション全体の成功/失敗と、ワークフロー関数の戻り値
        """
        from src.utils.logging_config import get_logger
        from src.utils.slack_notifier import SlackNotifier
        
        logger = get_logger(__name__)
        workflow_params = workflow_params or {}
        browser = None
        login = None
        workflow_results = None
        
        try:
            logger.info("=== PORTERSシステムセッションを開始します ===")
            
            # PORTERSへのログイン
            success, browser, login = cls.login_to_porters(
                selectors_path=selectors_path, 
                headless=headless
            )
            
            if not success:
                logger.error("ログイン処理に失敗したため、処理を中止します")
                return False, None
                
            logger.info("ログイン処理が完了しました")
            
            # ワークフロー関数を実行
            logger.info(f"ワークフロー処理を開始します: {workflow_func.__name__}")
            workflow_success = False
            
            try:
                # ワークフローにブラウザとログインオブジェクトを渡す
                workflow_results = workflow_func(browser=browser, login=login, **workflow_params)
                
                # 戻り値がタプルまたはリストの場合、最初の要素を成功/失敗フラグとして扱う
                if isinstance(workflow_results, (tuple, list)) and len(workflow_results) > 0:
                    workflow_success = bool(workflow_results[0])
                else:
                    workflow_success = bool(workflow_results)
                
                if workflow_success:
                    logger.info(f"ワークフロー処理が正常に完了しました: {workflow_func.__name__}")
                else:
                    logger.error(f"ワークフロー処理に失敗しました: {workflow_func.__name__}")
            except Exception as e:
                error_message = f"ワークフロー処理中に例外が発生しました: {workflow_func.__name__}"
                logger.error(f"{error_message}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                # エラー通知
                if browser:
                    browser._notify_error(
                        error_message,
                        exception=e,
                        context={"ワークフロー": workflow_func.__name__, "パラメータ": str(workflow_params)}
                    )
            
            # ログアウト処理
            if login:
                try:
                    logger.info("ログアウト処理を開始します")
                    logout_result = login.logout()
                    if logout_result:
                        logger.info("ログアウト処理が正常に完了しました")
                    else:
                        logger.warning("ログアウト処理に失敗しました")
                except Exception as e:
                    logger.error(f"ログアウト処理中に例外が発生しました: {str(e)}")
            
            # 操作完了後の待機時間
            import time
            logger.info("操作完了後、3秒間待機します")
            time.sleep(3)
            
            return workflow_success, workflow_results
            
        except Exception as e:
            error_message = "PORTERSシステムセッション処理中に例外が発生しました"
            logger.error(f"{error_message}: {str(e)}")
            import traceback
            trace = traceback.format_exc()
            logger.error(trace)
            
            # インスタンスが作成されていればSlack通知
            if 'browser' in locals() and browser:
                browser._notify_error(
                    error_message, 
                    exception=e, 
                    context={
                        "ワークフロー": workflow_func.__name__ if workflow_func else "不明",
                        "ヘッドレスモード": str(headless),
                        "セレクタパス": str(selectors_path)
                    }
                )
            else:
                # インスタンスがなければ一時的なSlackNotifierを作成して通知
                slack = SlackNotifier()
                slack.send_error(
                    error_message=error_message,
                    exception=e,
                    title="PORTERSシステムセッションエラー",
                    context={
                        "ワークフロー": workflow_func.__name__ if workflow_func else "不明",
                        "ヘッドレスモード": str(headless),
                        "セレクタパス": str(selectors_path)
                    }
                )
            
            return False, None
            
        finally:
            # 必ずブラウザを終了する
            if browser:
                logger.info("ブラウザを終了します")
                try:
                    # ワークフローが成功しなかった場合はエラーメッセージを含めて終了
                    if not workflow_success:
                        browser.quit(
                            error_message="ワークフロー処理が正常に完了しませんでした", 
                            context={
                                "ワークフロー": workflow_func.__name__ if workflow_func else "不明",
                                "ヘッドレスモード": str(headless),
                                "セレクタパス": str(selectors_path)
                            }
                        )
                    else:
                        browser.quit()
                    logger.info("ブラウザを正常に終了しました")
                except Exception as e:
                    logger.error(f"ブラウザの終了中に例外が発生しました: {str(e)}") 

    def get_window_handles(self):
        """
        現在のウィンドウハンドルのリストを取得する
        
        Returns:
            list: ウィンドウハンドルのリスト。エラーが発生した場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            return self.driver.window_handles
        except Exception as e:
            error_message = "ウィンドウハンドル取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return []

    def get_page_source(self):
        """
        現在のページのHTMLソースを取得する
        
        Returns:
            str: HTMLソース。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.page_source
        except Exception as e:
            error_message = "ページソース取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def get_current_url(self):
        """
        現在のページのURLを取得する
        
        Returns:
            str: 現在のURL。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.current_url
        except Exception as e:
            error_message = "URL取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def get_page_title(self):
        """
        現在のページのタイトルを取得する
        
        Returns:
            str: ページタイトル。エラーが発生した場合は空文字列
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return ""
            return self.driver.title
        except Exception as e:
            error_message = "ページタイトル取得中にエラーが発生しました"
            self._notify_error(error_message, e)
            return ""

    def execute_script(self, script, *args):
        """
        JavaScriptを実行する
        
        Args:
            script (str): 実行するJavaScriptコード
            *args: JavaScriptに渡す引数
            
        Returns:
            any: JavaScriptの実行結果。エラーが発生した場合はNone
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return None
            return self.driver.execute_script(script, *args)
        except Exception as e:
            error_message = "JavaScriptの実行中にエラーが発生しました"
            self._notify_error(error_message, e)
            return None

    def scroll_to_element(self, element, position="center"):
        """
        要素が画面内に表示されるようにスクロールする
        
        Args:
            element (WebElement): スクロール対象の要素
            position (str): スクロール位置（"start", "center", "end", "nearest"）
            
        Returns:
            bool: スクロールが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return False
            self.driver.execute_script(f"arguments[0].scrollIntoView({{block: '{position}'}});", element)
            time.sleep(1)  # スクロール完了を待機
            return True
        except Exception as e:
            error_message = "要素へのスクロール中にエラーが発生しました"
            self._notify_error(error_message, e)
            return False

    def find_elements(self, by, value):
        """
        指定されたセレクタに一致する複数の要素を取得する
        
        Args:
            by (By): 検索方法（By.CSS_SELECTOR, By.XPATHなど）
            value (str): セレクタの値
            
        Returns:
            list: 見つかった要素のリスト。見つからない場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            return self.driver.find_elements(by, value)
        except Exception as e:
            error_message = f"要素の検索中にエラーが発生しました: {by}={value}"
            self._notify_error(error_message, e)
            return []

    def find_elements_by_tag(self, tag, text_filter=None):
        """
        指定されたタグ名の要素を検索し、オプションでテキスト内容でフィルタリングする
        
        Args:
            tag (str): 検索するHTML要素のタグ名
            text_filter (str, optional): 要素のテキストに含まれるべき文字列
            
        Returns:
            list: 見つかった要素のリスト。見つからない場合は空リスト
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return []
            
            elements = self.driver.find_elements(By.TAG_NAME, tag)
            
            if text_filter:
                filtered_elements = []
                for element in elements:
                    try:
                        if text_filter in element.text:
                            filtered_elements.append(element)
                    except:
                        continue
                return filtered_elements
            
            return elements
        except Exception as e:
            error_message = f"{tag}タグの要素検索中にエラーが発生しました"
            self._notify_error(error_message, e)
            return []

    def wait_for_element(self, by, value, condition=EC.presence_of_element_located, timeout=None):
        """
        指定された条件で要素を待機する
        
        Args:
            by (By): 検索方法（By.CSS_SELECTOR, By.XPATHなど）
            value (str): セレクタの値
            condition (function, optional): 待機条件。デフォルトはEC.presence_of_element_located
            timeout (int, optional): タイムアウト時間（秒）。未指定時はデフォルトのタイムアウトを使用
            
        Returns:
            WebElement: 見つかった要素。見つからない場合はNone
        """
        try:
            if not self.driver:
                logger.error("WebDriverが初期化されていません")
                return None
            
            wait_timeout = timeout or self.timeout
            return WebDriverWait(self.driver, wait_timeout).until(
                condition((by, value))
            )
        except TimeoutException:
            logger.warning(f"要素の待機中にタイムアウトが発生しました: {by}={value}")
            return None
        except Exception as e:
            error_message = f"要素の待機中にエラーが発生しました: {by}={value}"
            self._notify_error(error_message, e)
            return None 