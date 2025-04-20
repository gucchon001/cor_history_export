#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PORTERSシステムの業務操作を管理するモジュール

このモジュールは、PORTERSシステムでの「その他業務」ボタンのクリックや
メニュー項目の選択など、業務操作に関する機能を提供します。
"""

import os
import time
import glob
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from pathlib import Path
from typing import Optional
import re
import importlib.util

from src.utils.logging_config import get_logger
from src.utils.helpers import find_latest_csv_in_downloads
from src.utils.environment import EnvironmentUtils as env

logger = get_logger(__name__)

class PortersOperations:
    """
    PORTERSシステムの業務操作を管理するクラス
    
    このクラスは、PORTERSシステムでの「その他業務」ボタンのクリックや
    メニュー項目の選択など、業務操作に関する機能を提供します。
    """
    
    def __init__(self, browser):
        """
        業務操作クラスの初期化
        
        Args:
            browser (PortersBrowser): ブラウザ操作を管理するインスタンス
        """
        self.browser = browser
        self.screenshot_dir = browser.screenshot_dir
    
    def click_other_operations_button(self):
        """
        「その他業務」ボタンをクリックして新しいウィンドウに切り替える
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 「その他業務」ボタンのクリック処理を開始します ===")
            
            # 現在のウィンドウハンドルを保存
            current_handles = self.browser.get_window_handles()
            logger.info(f"現在のウィンドウハンドル: {current_handles}")
            
            # 「その他業務」ボタンをクリック
            if not self.browser.click_element('porters_menu', 'search_button', use_javascript=True):
                logger.error("「その他業務」ボタンのクリックに失敗しました")
                return False
            
            # 新しいウィンドウに切り替え
            if not self.browser.switch_to_new_window(current_handles):
                logger.error("新しいウィンドウへの切り替えに失敗しました")
                return False
            
            # 新しいウィンドウでのページ状態を確認
            new_window_html = self.browser.get_page_source()
            html_path = os.path.join(self.screenshot_dir, "new_window.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(new_window_html)
            logger.info("新しいウィンドウのHTMLを保存しました")
            
            logger.info("✅ 「その他業務」ボタンのクリックと新しいウィンドウへの切り替えが完了しました")
            return True
            
        except Exception as e:
            logger.error(f"「その他業務」ボタンのクリック処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("other_operations_error.png")
            return False
    
    def click_history_menu(self):
        """
        対応履歴メニューをクリックする
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 対応履歴メニューのクリック処理を開始します ===")
            
            # 対応履歴メニューをクリック
            if not self.browser.click_element('porters_menu', 'history_menu'):
                logger.error("対応履歴メニューのクリックに失敗しました")
                return False
            
            # 処理待機
            time.sleep(3)
            self.browser.save_screenshot("after_history_menu_click.png")
            
            logger.info("✅ 対応履歴メニューのクリック処理が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"対応履歴メニューのクリック処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("history_menu_error.png")
            return False
    
    def click_all_history(self):
        """
        「すべての対応履歴」リンクをクリックする
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 「すべての対応履歴」リンクのクリック処理を開始します ===")
            
            # 処理待機 - メニューが完全に表示されるまで待機
            time.sleep(5)
            
            # まずテキスト内容で「すべての対応履歴」リンクを探索
            logger.info("テキスト内容で「すべての対応履歴」リンクを探索します")
            links = self.browser.find_elements_by_tag("a", "すべての対応履歴")
            if links:
                self.browser.click_element_direct(links[0])
                logger.info("✓ テキスト内容で「すべての対応履歴」リンクをクリックしました")
            else:
                logger.warning("テキスト内容での「すべての対応履歴」リンクの探索に失敗しました。セレクタを使用して再試行します。")
                
                # セレクタが動的に変わる可能性があるため、登録済みセレクタを使用
                if not self.browser.click_element('porters_menu', 'all_history_list'):
                    logger.error("登録済みセレクタでの「すべての対応履歴」リンクのクリックに失敗しました")
                    
                    # 直接CSSセレクタを使用して再試行
                    try:
                        logger.info("直接CSSセレクタを使用して「すべての対応履歴」リンクを探索します")
                        all_history_selector = "#ui-id-367 > li:nth-child(4) > a"
                        all_history_element = self.browser.wait_for_element(
                            By.CSS_SELECTOR, 
                            all_history_selector,
                            condition=EC.element_to_be_clickable
                        )
                        
                        if all_history_element:
                            self.browser.click_element_direct(all_history_element)
                            logger.info("✓ 直接CSSセレクタを使用して「すべての対応履歴」リンクをクリックしました")
                        else:
                            logger.error("直接CSSセレクタを使用しても「すべての対応履歴」リンクが見つかりませんでした")
                            return False
                    except Exception as css_e:
                        logger.error(f"直接CSSセレクタを使用したクリックにも失敗しました: {str(css_e)}")
                        return False
            
            # 処理待機
            time.sleep(3)
            self.browser.save_screenshot("after_all_history_click.png")
            
            # ページ内容を確認
            page_html = self.browser.get_page_source()
            page_analysis = self.browser.analyze_page_content(page_html)
            logger.info(f"ページタイトル: {page_analysis['page_title']}")
            
            logger.info("✅ 「すべての対応履歴」リンクのクリック処理が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"「すべての対応履歴」リンクのクリック処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("all_history_error.png")
            return False
    
    def select_all_correspondence(self):
        """
        対応履歴一覧画面で「全てチェック」チェックボックスをクリックする
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 「全てチェック」チェックボックスのクリック処理を開始します ===")
            
            # 画面の読み込みを待機
            time.sleep(3)
            self.browser.save_screenshot("before_select_all.png")
            
            # 「全てチェック」チェックボックスをクリック
            if not self.browser.click_element('correspondence_list', 'select_all_checkbox'):
                logger.error("「全てチェック」チェックボックスのクリックに失敗しました")
                
                # 直接CSSセレクタを使用して再試行
                try:
                    logger.info("直接CSSセレクタを使用して「全てチェック」チェックボックスを探索します")
                    checkbox_selector = "#recordListView > div.jss37 > div:nth-child(2) > div > div.jss45 > span > span > input"
                    checkbox_element = self.browser.wait_for_element(
                        By.CSS_SELECTOR, 
                        checkbox_selector,
                        condition=EC.element_to_be_clickable,
                        timeout=10
                    )
                    
                    if checkbox_element:
                        # チェックボックスが見つかった場合
                        self.browser.click_element_direct(checkbox_element)
                        logger.info("✓ 直接CSSセレクタを使用して「全てチェック」チェックボックスをクリックしました")
                    else:
                        # 一般的なチェックボックスセレクタを試す
                        logger.warning("具体的なセレクタが見つかりませんでした。一般的なチェックボックスを探索します。")
                        checkbox_selector = "#recordListView input[type='checkbox']"
                        checkbox_element = self.browser.wait_for_element(
                            By.CSS_SELECTOR, 
                            checkbox_selector,
                            condition=EC.element_to_be_clickable,
                            timeout=10
                        )
                        if checkbox_element:
                            self.browser.click_element_direct(checkbox_element)
                            logger.info("✓ 一般的なセレクタを使用して「全てチェック」チェックボックスをクリックしました")
                        else:
                            logger.error("すべてのセレクタで「全てチェック」チェックボックスが見つかりませんでした")
                            return False
                except Exception as css_e:
                    logger.error(f"直接CSSセレクタを使用したクリックにも失敗しました: {str(css_e)}")
                    return False
            
            # 処理待機
            time.sleep(2)
            self.browser.save_screenshot("after_select_all.png")
            
            logger.info("✅ 「全てチェック」チェックボックスのクリック処理が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"「全てチェック」チェックボックスのクリック処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("select_all_error.png")
            return False
    
    def click_show_more_repeatedly(self, max_attempts=20, interval=5):
        """
        「もっと見る」ボタンを繰り返しクリックして、すべての対応履歴を表示する
        
        Args:
            max_attempts (int): 最大試行回数
            interval (int): クリック間隔（秒）
            
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 「もっと見る」ボタンの繰り返しクリック処理を開始します ===")
            
            # 「もっと見る」ボタンが見つからなくなるまで繰り返しクリック
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                logger.info(f"「もっと見る」ボタンのクリック試行: {attempt}/{max_attempts}")
                
                # スクリーンショットを取得
                self.browser.save_screenshot(f"show_more_attempt_{attempt}.png")
                
                # 「もっと見る」ボタンを探す（クラス名で検索）
                try:
                    # まずセレクタ情報を使用
                    show_more_button = None
                    try:
                        show_more_button = self.browser.get_element('correspondence_list', 'show_more_button')
                    except:
                        pass
                    
                    # セレクタ情報で見つからない場合、クラス名で検索
                    if not show_more_button:
                        logger.info("クラス名で「もっと見る」ボタンを探索します")
                        show_more_button = WebDriverWait(self.browser.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.list-view-show-more-button"))
                        )
                    
                    # ボタンが見つからない場合、テキスト内容で検索
                    if not show_more_button:
                        logger.info("テキスト内容で「もっと見る」ボタンを探索します")
                        buttons = self.browser.driver.find_elements(By.TAG_NAME, "button")
                        for button in buttons:
                            if "もっと見る" in button.text:
                                logger.info(f"「もっと見る」テキストを含むボタンを発見しました: {button.text}")
                                show_more_button = button
                                break
                    
                    # ボタンが見つかった場合、クリック
                    if show_more_button:
                        # 要素が画面内に表示されるようにスクロール
                        self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_more_button)
                        time.sleep(1)  # スクロール完了を待機
                        
                        # クリック実行
                        show_more_button.click()
                        logger.info(f"✓ 「もっと見る」ボタンをクリックしました（{attempt}回目）")
                        
                        # 次のデータ読み込みを待機
                        time.sleep(interval)
                    else:
                        logger.info("「もっと見る」ボタンが見つかりませんでした。すべてのデータが表示されたと思われます。")
                        break
                        
                except TimeoutException:
                    logger.info("「もっと見る」ボタンが見つかりませんでした。すべてのデータが表示されたと思われます。")
                    break
                except Exception as e:
                    logger.warning(f"{attempt}回目の「もっと見る」ボタンクリック中にエラーが発生しましたが、処理を継続します: {str(e)}")
                    # エラーが発生しても処理を継続
                    time.sleep(interval)
            
            # 「もっと見る」ボタンがなくなった後、データグリッドコンテナを一番下までスクロール
            logger.info("データグリッドコンテナを一番下までスクロールします")
            
            # データグリッドコンテナを探す（複数のセレクタを試す）
            data_grid_container = None
            grid_selectors = [
                "#dataGridContainer",
                ".data-grid-container",
                "#recordListView div[role='grid']",
                "#recordListView .jss37",
                "#recordListView .MuiTable-root",
                "#recordListView table",
                "div[role='grid']",
                ".grid-container",
                ".table-container"
            ]
            
            for selector in grid_selectors:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        data_grid_container = elements[0]
                        logger.info(f"データグリッドコンテナを発見しました: {selector}")
                        break
                except Exception:
                    continue
            
            if data_grid_container:
                try:
                    # コンテナの高さ情報を取得
                    container_height = self.browser.driver.execute_script("return arguments[0].scrollHeight", data_grid_container)
                    logger.info(f"データグリッドコンテナの高さ: {container_height}px")
                    
                    # 段階的にスクロールして、すべてのデータを確実に読み込む
                    scroll_steps = 5  # スクロールのステップ数
                    for step in range(1, scroll_steps + 1):
                        scroll_position = int(container_height * step / scroll_steps)
                        self.browser.driver.execute_script(f"arguments[0].scrollTop = {scroll_position}", data_grid_container)
                        logger.info(f"データグリッドコンテナをスクロール: {scroll_position}px ({step}/{scroll_steps})")
                        time.sleep(1)  # 各ステップ後に少し待機
                    
                    # 最後に一番下までスクロール
                    self.browser.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", data_grid_container)
                    logger.info("データグリッドコンテナを一番下までスクロールしました")
                    
                    # スクロール完了を待機
                    time.sleep(3)
                    self.browser.save_screenshot("after_grid_scroll_bottom.png")
                    
                except Exception as e:
                    logger.warning(f"データグリッドコンテナのスクロール中にエラーが発生しました: {str(e)}")
                    self._scroll_page_fallback()
            else:
                logger.warning("データグリッドコンテナが見つかりませんでした")
                self._scroll_page_fallback()
            
            # 最終的な画面のスクリーンショットを取得
            self.browser.save_screenshot("after_show_more_all.png")
            
            logger.info(f"✅ 「もっと見る」ボタンの繰り返しクリック処理が完了しました（{attempt}回実行）")
            return True
            
        except Exception as e:
            logger.error(f"「もっと見る」ボタンの繰り返しクリック処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("show_more_error.png")
            return False
    
    def _scroll_page_fallback(self):
        """
        ページ全体をスクロールするフォールバック処理
        
        データグリッドコンテナが見つからない場合や、
        スクロールに失敗した場合に使用する代替手段
        """
        try:
            logger.info("代替手段: ページ全体を一番下までスクロールします")
            
            # ページの高さを取得
            page_height = self.browser.driver.execute_script("return document.body.scrollHeight")
            logger.info(f"ページの高さ: {page_height}px")
            
            # 段階的にスクロール
            scroll_steps = 5
            for step in range(1, scroll_steps + 1):
                scroll_position = int(page_height * step / scroll_steps)
                self.browser.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                logger.info(f"ページを段階的にスクロール: {scroll_position}px ({step}/{scroll_steps})")
                time.sleep(1)
            
            # 最後に一番下までスクロール
            self.browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.browser.save_screenshot("after_page_scroll_bottom.png")
            
            # 一番上に戻ってから再度一番下までスクロール
            self.browser.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
        except Exception as scroll_e:
            logger.warning(f"ページ全体のスクロール中にエラーが発生しました: {str(scroll_e)}")
    
    def export_history_data(self) -> bool:
        """
        対応履歴データをエクスポートする
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 対応履歴データのエクスポート処理を開始します ===")
            
            # アクションリストボタンをクリック
            if not self.browser.click_element('correspondence_list', 'action_button'):
                logger.error("アクションリストボタンのクリックに失敗しました")
                
                # 直接CSSセレクタを使用してアクションボタンを探索します
                try:
                    logger.info("直接CSSセレクタを使用してアクションボタンを探索します")
                    action_button_selector = "#recordListView > div.jss37 > div:nth-child(2) > div > button > div"
                    action_button_element = WebDriverWait(self.browser.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, action_button_selector))
                    )
                    action_button_element.click()
                    logger.info("✓ 直接CSSセレクタを使用してアクションボタンをクリックしました")
                except Exception as css_e:
                    logger.error(f"直接CSSセレクタを使用したクリックにも失敗しました: {str(css_e)}")
                    return False
            else:
                logger.info("✓ アクションリストボタンをクリックしました")
            
            # エクスポートボタンをクリック
            logger.info("エクスポートボタンをクリックします")
            export_button_clicked = False
            
            # 1. まずテキスト内容で「エクスポート」を含む要素を探す
            try:
                logger.info("テキスト内容で「エクスポート」を含む要素を探索します")
                elements = self.browser.driver.find_elements(By.TAG_NAME, "li")
                for element in elements:
                    try:
                        element_text = element.text.strip()
                        element_class = element.get_attribute("class") or ""
                        if "エクスポート" in element_text and ("linkExport" in element_class or "export" in element_class.lower()):
                            logger.info(f"「エクスポート」テキストを含む要素を発見しました: {element_text} (class={element_class})")
                            element.click()
                            logger.info("✓ テキスト内容でエクスポートボタンをクリックしました")
                            export_button_clicked = True
                            break
                    except Exception as elem_e:
                        logger.debug(f"要素の確認中にエラー: {str(elem_e)}")
                        continue
            except Exception as text_e:
                logger.warning(f"テキスト内容での探索中にエラーが発生しました: {str(text_e)}")
            
            # 2. テキスト検索で見つからなかった場合、セレクタを使用
            if not export_button_clicked:
                if not self.browser.click_element('correspondence_list', 'export_button'):
                    logger.error("セレクタでのエクスポートボタンのクリックに失敗しました")
                    
                    # 3. 代替セレクタを使用して再試行
                    try:
                        logger.info("直接CSSセレクタを使用してエクスポートボタンを探索します")
                        export_button_selector = "#pageActivity > div:nth-child(27) > div > ul > li.jss194.linkExport"
                        export_button_element = WebDriverWait(self.browser.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, export_button_selector))
                        )
                        export_button_element.click()
                        logger.info("✓ 直接CSSセレクタを使用してエクスポートボタンをクリックしました")
                        export_button_clicked = True
                    except Exception as css_e:
                        logger.warning(f"直接CSSセレクタを使用したクリックに失敗しました: {str(css_e)}")
                        
                        # 4. クラス名で試す
                        try:
                            logger.info("クラス名でエクスポートボタンを探索します")
                            export_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "li.linkExport")
                            if export_elements:
                                export_elements[0].click()
                                logger.info("✓ クラス名でエクスポートボタンをクリックしました")
                                export_button_clicked = True
                        except Exception as class_e:
                            logger.warning(f"クラス名でのエクスポートボタンクリックに失敗しました: {str(class_e)}")
                        
                        # 5. XPathを使用して再試行
                        if not export_button_clicked:
                            try:
                                logger.info("XPathを使用してエクスポートボタンを探索します")
                                export_button_xpath = "//*[contains(@class, 'linkExport')]"
                                export_button_element = WebDriverWait(self.browser.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, export_button_xpath))
                                )
                                export_button_element.click()
                                logger.info("✓ XPathを使用してエクスポートボタンをクリックしました")
                                export_button_clicked = True
                            except Exception as xpath_e:
                                logger.error(f"XPathを使用したクリックにも失敗しました: {str(xpath_e)}")
                else:
                    logger.info("✓ セレクタでエクスポートボタンをクリックしました")
                    export_button_clicked = True
            
            if not export_button_clicked:
                logger.error("すべての方法でエクスポートボタンのクリックに失敗しました")
                return False
                
            logger.info("✓ エクスポートボタンのクリックに成功しました")
            
            # 検索画面を開くボタンをクリック
            try:
                logger.info("検索画面を開くボタンをクリックします")
                if self.browser.click_element('export_dialog', 'all_raw_data'):
                    logger.info("✓ 検索画面を開くボタンをクリックしました")
                else:
                    # テキストで検索
                    try:
                        logger.info("テキストで検索画面を開くボタンを探索します")
                        buttons = self.browser.driver.find_elements(By.TAG_NAME, "button")
                        for button in buttons:
                            if "検索画面" in button.text or "search" in button.get_attribute("class").lower():
                                logger.info(f"検索関連のボタンを発見しました: {button.text}")
                                button.click()
                                logger.info("✓ テキスト内容で検索画面を開くボタンをクリックしました")
                                break
                        else:
                            logger.error("検索関連のボタンが見つかりませんでした")
                            return False
                    except Exception as text_e:
                        logger.error(f"テキスト検索での代替手段にも失敗しました: {str(text_e)}")
                        return False
                
                # 検索画面が表示されるまで待機
                time.sleep(3)
                
                # 登録先プルダウンから「企業」を選択
                try:
                    logger.info("登録先プルダウンから「企業」を選択します")
                    
                    # セレクタから登録先プルダウン要素を取得
                    registered_to_element = self.browser.get_element('export_dialog', 'registered_to')
                    if registered_to_element:
                        # Selectオブジェクトを作成
                        from selenium.webdriver.support.ui import Select
                        select = Select(registered_to_element)
                        
                        # テキストで「企業」を含むオプションを選択
                        try:
                            select.select_by_visible_text("企業")
                            logger.info("✓ 「企業」オプションを選択しました")
                        except:
                            # テキストが完全一致しない場合、部分一致で検索
                            options = select.options
                            for option in options:
                                if "企業" in option.text:
                                    option.click()
                                    logger.info(f"✓ 「{option.text}」オプションを選択しました")
                                    break
                            else:
                                # JavaScriptで直接値を設定する代替手段
                                self.browser.execute_script("arguments[0].value = '企業';", registered_to_element)
                                logger.info("✓ JavaScriptで「企業」の値を設定しました")
                    else:
                        logger.error("登録先プルダウン要素が見つかりませんでした")
                        # 処理を継続するために失敗してもスキップ
                except Exception as e:
                    logger.error(f"登録先プルダウンの操作中にエラーが発生しました: {str(e)}")
                    self.browser.save_screenshot("register_to_select_error.png")
                    # 処理を継続するために失敗してもスキップ
                
                # 検索ボタンをクリック
                try:
                    logger.info("検索ボタンをクリックします")
                    if self.browser.click_element('export_dialog', 'execute_search'):
                        logger.info("✓ 検索ボタンをクリックしました")
                    else:
                        # 直接クリックを試みる
                        try:
                            search_button = self.browser.wait_for_element(
                                By.CSS_SELECTOR, "#execute_search", 
                                condition=EC.element_to_be_clickable, 
                                timeout=10
                            )
                            if search_button:
                                search_button.click()
                                logger.info("✓ 直接CSSセレクタで検索ボタンをクリックしました")
                            else:
                                logger.error("検索ボタンが見つかりませんでした")
                                return False
                        except Exception as e:
                            logger.error(f"検索ボタンクリック処理中にエラーが発生しました: {str(e)}")
                            return False
                except Exception as e:
                    logger.error(f"検索ボタンクリック処理中にエラーが発生しました: {str(e)}")
                    self.browser.save_screenshot("execute_search_error.png")
                    return False
                
                # 検索結果が表示されるまで待機
                time.sleep(3)
                self.browser.save_screenshot("after_search_button_click.png")
                
            except Exception as e:
                logger.error(f"検索ダイアログの操作中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("search_dialog_error.png")
                return False
            
            # 検索結果処理：全てチェック → アクションボタン → エクスポート
            try:
                logger.info("検索結果の処理を開始します")
                
                # 1. 「全てチェック」チェックボックスをクリック
                logger.info("検索結果の「全てチェック」チェックボックスをクリックします")
                checkbox_clicked = False
                
                # 標準セレクタでクリック
                if self.browser.click_element('correspondence_list', 'select_all_checkbox'):
                    logger.info("✓ 「全てチェック」チェックボックスをクリックしました")
                    checkbox_clicked = True
                else:
                    # 代替セレクタで試行
                    try:
                        checkbox_selectors = [
                            "#recordListView > div.jss37 > div:nth-child(2) > div > div.jss45 > span > span > input",
                            "#recordListView input[type='checkbox']",
                            ".jss45 input[type='checkbox']",
                            "input[type='checkbox']"
                        ]
                        
                        for selector in checkbox_selectors:
                            try:
                                logger.info(f"代替セレクタ '{selector}' でチェックボックスを探索します")
                                elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements and len(elements) > 0:
                                    # 最初のチェックボックスをクリック（通常は全選択チェックボックス）
                                    elements[0].click()
                                    logger.info(f"✓ 代替セレクタ '{selector}' でチェックボックスをクリックしました")
                                    checkbox_clicked = True
                                    break
                            except Exception as selector_e:
                                logger.warning(f"セレクタ '{selector}' での探索中にエラー: {str(selector_e)}")
                    except Exception as e:
                        logger.warning(f"チェックボックス選択の代替処理中にエラー: {str(e)}")
                
                if not checkbox_clicked:
                    logger.warning("チェックボックスの選択ができませんでした。処理を続行します。")
                
                # 選択後、少し待機
                time.sleep(2)
                self.browser.save_screenshot("after_checkbox_clicked.png")
                
                # 2. 「アクションボタン」をクリック
                logger.info("検索結果の「アクションボタン」をクリックします")
                action_button_clicked = False
                
                # 標準セレクタでクリック
                if self.browser.click_element('correspondence_list', 'action_button'):
                    logger.info("✓ 「アクションボタン」をクリックしました")
                    action_button_clicked = True
                else:
                    # 代替セレクタで試行
                    try:
                        action_selectors = [
                            "#recordListView > div.jss37 > div:nth-child(2) > div > button > div",
                            "#recordListView button",
                            ".jss37 button"
                        ]
                        
                        for selector in action_selectors:
                            try:
                                logger.info(f"代替セレクタ '{selector}' でアクションボタンを探索します")
                                elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements and len(elements) > 0:
                                    # 最初のボタンをクリック
                                    elements[0].click()
                                    logger.info(f"✓ 代替セレクタ '{selector}' でアクションボタンをクリックしました")
                                    action_button_clicked = True
                                    break
                            except Exception as selector_e:
                                logger.warning(f"セレクタ '{selector}' での探索中にエラー: {str(selector_e)}")
                    except Exception as e:
                        logger.warning(f"アクションボタン選択の代替処理中にエラー: {str(e)}")
                
                if not action_button_clicked:
                    logger.error("アクションボタンをクリックできませんでした")
                    self.browser.save_screenshot("action_button_failed.png")
                    return False
                
                # クリック後、少し待機
                time.sleep(2)
                self.browser.save_screenshot("after_action_button_clicked.png")
                
                # 3. 「エクスポート」をクリック
                logger.info("「エクスポート」ボタンをクリックします")
                export_button_clicked = False
                
                # まずテキスト内容で「エクスポート」を含む要素を探す
                try:
                    logger.info("テキスト内容で「エクスポート」を含む要素を探索します")
                    elements = self.browser.driver.find_elements(By.TAG_NAME, "li")
                    for element in elements:
                        try:
                            element_text = element.text.strip()
                            element_class = element.get_attribute("class") or ""
                            if "エクスポート" in element_text:
                                logger.info(f"「エクスポート」テキストを含む要素を発見しました: {element_text} (class={element_class})")
                                element.click()
                                logger.info("✓ テキスト内容でエクスポートボタンをクリックしました")
                                export_button_clicked = True
                                break
                        except Exception as elem_e:
                            logger.debug(f"要素の確認中にエラー: {str(elem_e)}")
                            continue
                except Exception as text_e:
                    logger.warning(f"テキスト内容での探索中にエラーが発生しました: {str(text_e)}")
                
                # テキスト検索で見つからなかった場合、セレクタを使用
                if not export_button_clicked:
                    if self.browser.click_element('correspondence_list', 'export_button'):
                        logger.info("✓ セレクタでエクスポートボタンをクリックしました")
                        export_button_clicked = True
                
                if not export_button_clicked:
                    logger.error("エクスポートボタンをクリックできませんでした")
                    self.browser.save_screenshot("export_button_failed.png")
                    return False
                
                # クリック後、少し待機
                time.sleep(2)
                self.browser.save_screenshot("after_export_button_clicked.png")
                
            except Exception as e:
                logger.error(f"検索結果処理中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("search_result_process_error.png")
                return False
            
            # エクスポートオプションとして「企業対応履歴」をクリック
            try:
                logger.info("企業対応履歴オプションをクリックします")
                
                # 対応履歴エクスポートダイアログが表示されるまで待機
                time.sleep(5)
                self.browser.save_screenshot("before_company_history_option.png")

                # 現在のダイアログの情報を取得して分析
                dialogs = self.browser.driver.find_elements(By.CSS_SELECTOR, ".ui-dialog")
                if dialogs:
                    dialog_info = "検出されたダイアログ情報:\n"
                    for i, dialog in enumerate(dialogs):
                        dialog_id = dialog.get_attribute("id") or "不明"
                        dialog_class = dialog.get_attribute("class") or "不明"
                        dialog_info += f"ダイアログ {i+1}: ID={dialog_id}, クラス={dialog_class}\n"
                        
                        # ダイアログ内の要素を探索
                        try:
                            # タイトルを取得
                            title_elements = dialog.find_elements(By.CSS_SELECTOR, ".ui-dialog-title")
                            if title_elements:
                                dialog_info += f"  タイトル: {title_elements[0].text}\n"
                            
                            # ラジオボタン/チェックボックスを検索
                            radios = dialog.find_elements(By.CSS_SELECTOR, "input[type='radio'], span.ui-icon-check, label")
                            dialog_info += f"  検出された選択要素数: {len(radios)}\n"
                            for j, radio in enumerate(radios[:5]):  # 最初の5つだけ表示
                                radio_text = ""
                                try:
                                    # ラベルテキストを取得
                                    if radio.tag_name == "label":
                                        radio_text = radio.text
                                    else:
                                        # 親要素や隣接要素からテキストを探す
                                        parent = radio.find_element(By.XPATH, "./..")
                                        radio_text = parent.text
                                except:
                                    radio_text = "テキスト取得失敗"
                                
                                dialog_info += f"    選択要素 {j+1}: {radio_text} (タグ: {radio.tag_name})\n"
                        except Exception as dialog_ex:
                            dialog_info += f"  ダイアログ内要素の探索中にエラー: {str(dialog_ex)}\n"
                    
                    logger.info(dialog_info)
                    
                # 1. まず標準のセレクタでクリック試行
                if self.browser.click_element('export_dialog', 'company_history_option'):
                    logger.info("✓ 企業対応履歴オプションをクリックしました")
                else:
                    # 2. 直接CSSセレクタを複数試行
                    company_history_selectors = [
                        "#porters-pdialog_2 > div.mapping > div > div > div > ul > li:nth-child(2) > label > span",
                        "#porters-pdialog_2 label:contains('企業対応履歴')",
                        "div.mapping ul li:nth-child(2) label span",
                        "div.mapping ul li label span",
                        ".ui-dialog label span"
                    ]
                    
                    company_history_clicked = False
                    for selector in company_history_selectors:
                        try:
                            logger.info(f"セレクタ '{selector}' で企業対応履歴オプションを探索します")
                            elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements and len(elements) > 0:
                                # 各要素を順番に確認
                                for element in elements:
                                    try:
                                        element_text = ""
                                        try:
                                            # 要素のテキストを取得
                                            element_text = element.text
                                            if not element_text:
                                                # 親要素からテキストを取得
                                                parent = element.find_element(By.XPATH, "./..")
                                                element_text = parent.text
                                        except:
                                            element_text = "テキスト取得失敗"
                                            
                                        logger.info(f"候補要素を発見: '{element_text}'")
                                        
                                        # クリック試行
                                        element.click()
                                        logger.info(f"✓ セレクタ '{selector}' で企業対応履歴オプションをクリックしました")
                                        company_history_clicked = True
                                        break
                                    except Exception as element_e:
                                        logger.warning(f"要素クリック試行中にエラー: {str(element_e)}")
                                        continue
                                
                                if company_history_clicked:
                                    break
                        except Exception as selector_e:
                            logger.warning(f"セレクタ '{selector}' での探索中にエラー: {str(selector_e)}")
                            continue
                    
                    # 3. XPathを使用した複数のアプローチでチェック
                    if not company_history_clicked:
                        xpath_expressions = [
                            "//span[contains(text(), '企業') and contains(text(), '対応履歴')]",
                            "//label[contains(text(), '企業') and contains(text(), '対応履歴')]",
                            "//label[contains(text(), '企業')]",
                            "//input[@type='radio']/following::label[contains(text(), '企業')]",
                            "//div[contains(@class, 'mapping')]//label[contains(text(), '企業')]"
                        ]
                        
                        for xpath in xpath_expressions:
                            try:
                                logger.info(f"XPath '{xpath}' で企業対応履歴オプションを探索します")
                                xpath_elements = self.browser.driver.find_elements(By.XPATH, xpath)
                                if xpath_elements and len(xpath_elements) > 0:
                                    # 最初の要素をクリック
                                    xpath_elements[0].click()
                                    logger.info(f"✓ XPath '{xpath}' で企業対応履歴オプションをクリックしました")
                                    company_history_clicked = True
                                    break
                            except Exception as xpath_e:
                                logger.warning(f"XPath '{xpath}' での探索中にエラー: {str(xpath_e)}")
                                continue
                    
                    # 4. JavaScriptを使用したクリック
                    if not company_history_clicked:
                        try:
                            logger.info("JavaScriptを使用して企業対応履歴オプションをクリックします")
                            # ラジオボタン全てを取得
                            radio_buttons = self.browser.driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                            
                            if radio_buttons and len(radio_buttons) > 1:
                                # 2番目のラジオボタンを選択（多くの場合、企業対応履歴は2番目）
                                script = "arguments[0].click(); arguments[0].checked = true;"
                                self.browser.execute_script(script, radio_buttons[1])
                                logger.info("✓ JavaScriptで2番目のラジオボタンをクリックしました")
                                company_history_clicked = True
                            elif radio_buttons:
                                # 最初のラジオボタンを選択
                                script = "arguments[0].click(); arguments[0].checked = true;"
                                self.browser.execute_script(script, radio_buttons[0])
                                logger.info("✓ JavaScriptで最初のラジオボタンをクリックしました")
                                company_history_clicked = True
                        except Exception as js_e:
                            logger.warning(f"JavaScriptでのクリック中にエラー: {str(js_e)}")
                    
                    # 5. 最後の手段として、ダイアログ内のすべてのラジオボタンとラベルをクリック試行
                    if not company_history_clicked:
                        try:
                            logger.info("ダイアログ内のすべての選択可能要素をクリック試行します")
                            # ダイアログ内の全てのラジオボタン、チェックボックス、ラベルを取得
                            clickable_elements = self.browser.driver.find_elements(
                                By.CSS_SELECTOR, 
                                ".ui-dialog input[type='radio'], .ui-dialog label, .ui-dialog span.ui-icon-check"
                            )
                            
                            for i, elem in enumerate(clickable_elements):
                                try:
                                    logger.info(f"選択要素 {i+1}/{len(clickable_elements)} をクリック試行")
                                    elem.click()
                                    logger.info(f"✓ 選択要素 {i+1} のクリックに成功しました")
                                    company_history_clicked = True
                                    break
                                except:
                                    continue
                        except Exception as fallback_e:
                            logger.warning(f"最終手段でのクリック試行中にエラー: {str(fallback_e)}")
                    
                    if not company_history_clicked:
                        # すべての方法が失敗した場合はエラー
                        self.browser.save_screenshot("company_history_option_not_found.png")
                        # HTMLを保存して後で分析
                        html_path = os.path.join(self.browser.screenshot_dir, "dialog_html.html")
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(self.browser.driver.page_source)
                            
                        logger.error("すべての方法で企業対応履歴オプションのクリックに失敗しました")
                        return False
                
                # クリック後、少し待機してスクリーンショットを撮影
                time.sleep(2)
                self.browser.save_screenshot("after_company_history_option.png")
                
            except Exception as e:
                logger.error(f"企業対応履歴オプションのクリック中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("company_history_option_error.png")
                return False
            
            # 「次へ」ボタンをクリック（1/3）
            try:
                logger.info("「次へ」ボタン（1/3）をクリックします")
                
                # スクリーンショットを撮影して現在のダイアログの状態を確認
                self.browser.save_screenshot("before_next_button.png")
                
                # 現在のダイアログボタンペインの情報を取得して分析
                next_button_clicked = False
                
                # 1. すべてのダイアログを取得
                dialogs = self.browser.driver.find_elements(By.CSS_SELECTOR, ".ui-dialog")
                if dialogs:
                    button_info = "ダイアログ内のボタン情報:\n"
                    for i, dialog in enumerate(dialogs):
                        button_info += f"ダイアログ {i+1}:\n"
                        try:
                            # ボタンペインを探す
                            button_panes = dialog.find_elements(By.CSS_SELECTOR, ".ui-dialog-buttonpane")
                            if button_panes:
                                for j, pane in enumerate(button_panes):
                                    button_info += f"  ボタンペイン {j+1}:\n"
                                    # すべてのボタンを取得
                                    buttons = pane.find_elements(By.CSS_SELECTOR, "button")
                                    button_info += f"    ボタン数: {len(buttons)}\n"
                                    
                                    for k, button in enumerate(buttons):
                                        button_text = button.text.strip()
                                        button_class = button.get_attribute("class") or "不明"
                                        button_info += f"    ボタン {k+1}: テキスト=[{button_text}], クラス={button_class}\n"
                                        
                                        # 「次へ」ボタンかどうかを判断
                                        if "次へ" in button_text or "next" in button_text.lower():
                                            try:
                                                # 直接クリック
                                                button.click()
                                                logger.info(f"✓ ダイアログ内の「{button_text}」ボタンをクリックしました")
                                                next_button_clicked = True
                                                break
                                            except Exception as click_e:
                                                logger.warning(f"ボタン「{button_text}」のクリック中にエラー: {str(click_e)}")
                                                
                                                # JavaScriptでクリック試行
                                                try:
                                                    self.browser.execute_script("arguments[0].click();", button)
                                                    logger.info(f"✓ JavaScriptでダイアログ内の「{button_text}」ボタンをクリックしました")
                                                    next_button_clicked = True
                                                    break
                                                except Exception as js_e:
                                                    logger.warning(f"JavaScriptによるボタン「{button_text}」のクリック中にエラー: {str(js_e)}")
                                    
                                    if next_button_clicked:
                                        break
                            else:
                                button_info += "  ボタンペインが見つかりませんでした\n"
                        except Exception as dialog_e:
                            button_info += f"  ダイアログの分析中にエラー: {str(dialog_e)}\n"
                        
                        # 次へボタンが見つかって正常にクリックできた場合は終了
                        if next_button_clicked:
                            break
                            
                    logger.info(button_info)
                
                # 2. 標準セレクタでクリック試行
                if not next_button_clicked:
                    if self.browser.click_element('export_dialog', 'next_button_1'):
                        logger.info("✓ セレクタで「次へ」ボタン（1/3）をクリックしました")
                        next_button_clicked = True
                
                # 3. 複数のCSSセレクタを試行
                if not next_button_clicked:
                    next_button_selectors = [
                        ".ui-dialog-buttonpane button:nth-child(1)",
                        ".ui-dialog-buttonpane button:nth-child(2)",
                        ".ui-dialog-buttonpane button:first-child",
                        ".ui-dialog-buttonset button:first-child",
                        ".ui-dialog-buttonset button"
                    ]
                    
                    for selector in next_button_selectors:
                        try:
                            logger.info(f"セレクタ '{selector}' で「次へ」ボタンを探索します")
                            elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            if elements and len(elements) > 0:
                                # 各要素を試す
                                for element in elements:
                                    try:
                                        element_text = element.text.strip()
                                        logger.info(f"ボタン要素を発見: '{element_text}'")
                                        
                                        if element_text == "" or "次へ" in element_text or "next" in element_text.lower():
                                            # クリック試行
                                            element.click()
                                            logger.info(f"✓ セレクタ '{selector}' で「次へ」ボタンをクリックしました")
                                            next_button_clicked = True
                                            break
                                    except Exception as element_e:
                                        logger.warning(f"要素クリック試行中にエラー: {str(element_e)}")
                                        
                                        # JavaScriptを使用してクリック試行
                                        try:
                                            self.browser.execute_script("arguments[0].click();", element)
                                            logger.info(f"✓ JavaScriptでセレクタ '{selector}' の要素をクリックしました")
                                            next_button_clicked = True
                                            break
                                        except Exception as js_e:
                                            logger.warning(f"JavaScriptによるクリック試行中にエラー: {str(js_e)}")
                                            continue
                            
                            if next_button_clicked:
                                break
                        except Exception as selector_e:
                            logger.warning(f"セレクタ '{selector}' での探索中にエラー: {str(selector_e)}")
                
                # 4. XPathを試行
                if not next_button_clicked:
                    next_button_xpaths = [
                        "//button[contains(text(), '次へ')]",
                        "//span[contains(text(), '次へ')]/parent::button",
                        "//div[contains(@class, 'ui-dialog-buttonpane')]//button[1]",
                        "//div[contains(@class, 'ui-dialog-buttonset')]//button[1]"
                    ]
                    
                    for xpath in next_button_xpaths:
                        try:
                            logger.info(f"XPath '{xpath}' で「次へ」ボタンを探索します")
                            xpath_elements = self.browser.driver.find_elements(By.XPATH, xpath)
                            
                            if xpath_elements and len(xpath_elements) > 0:
                                # 最初の要素をクリック
                                xpath_elements[0].click()
                                logger.info(f"✓ XPath '{xpath}' で「次へ」ボタンをクリックしました")
                                next_button_clicked = True
                                break
                        except Exception as xpath_e:
                            logger.warning(f"XPath '{xpath}' での探索中にエラー: {str(xpath_e)}")
                            
                            # JavaScriptを使用してクリック試行
                            try:
                                self.browser.execute_script("arguments[0].click();", xpath_elements[0])
                                logger.info(f"✓ JavaScriptでXPath '{xpath}' の要素をクリックしました")
                                next_button_clicked = True
                                break
                            except Exception as js_e:
                                logger.warning(f"JavaScriptによるクリック試行中にエラー: {str(js_e)}")
                
                # 5. 最後の手段として、すべてのボタンを順にクリック
                if not next_button_clicked:
                    try:
                        logger.info("すべてのダイアログボタンをクリック試行します")
                        all_buttons = self.browser.driver.find_elements(By.CSS_SELECTOR, ".ui-dialog button")
                        
                        for i, btn in enumerate(all_buttons):
                            try:
                                btn_text = btn.text.strip()
                                logger.info(f"ボタン {i+1}/{len(all_buttons)} をクリック試行: '{btn_text}'")
                                
                                # 一部のボタンはスキップ（キャンセル、閉じるなど）
                                if btn_text.lower() in ["cancel", "キャンセル", "閉じる", "close"]:
                                    logger.info(f"ボタン '{btn_text}' はスキップします")
                                    continue
                                
                                btn.click()
                                logger.info(f"✓ ボタン {i+1} '{btn_text}' のクリックに成功しました")
                                next_button_clicked = True
                                break
                            except:
                                # JavaScriptを使用してクリック試行
                                try:
                                    self.browser.execute_script("arguments[0].click();", btn)
                                    logger.info(f"✓ JavaScriptでボタン {i+1} '{btn_text}' をクリックしました")
                                    next_button_clicked = True
                                    break
                                except:
                                    continue
                    except Exception as fallback_e:
                        logger.warning(f"最終手段でのクリック試行中にエラー: {str(fallback_e)}")
                
                if not next_button_clicked:
                    self.browser.save_screenshot("next_button_not_found.png")
                    # HTMLを保存して後で分析
                    html_path = os.path.join(self.browser.screenshot_dir, "next_button_html.html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(self.browser.driver.page_source)
                    
                    logger.error("「次へ」ボタン（1/3）が見つからないか、クリックできませんでした")
                    return False
                
                # 次へボタンがクリックされた後、次の画面が表示されるまで待機
                time.sleep(3)
                self.browser.save_screenshot("after_next_button_click.png")
                
            except Exception as e:
                logger.error(f"「次へ」ボタン（1/3）のクリック中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("next_button_error.png")
                return False
            
            # 処理待機
            time.sleep(2)
            
            # 「次へ」ボタンをクリック（2/3）
            try:
                logger.info("「次へ」ボタン（2/3）をクリックします")
                if self.browser.click_element('export_dialog', 'next_button_2'):
                    logger.info("✓ 「次へ」ボタン（2/3）をクリックしました")
                else:
                    # 直接CSSセレクタまたはXPathを使用した代替手段（上記と同様）
                    next_button_finder = False
                    
                    # 1. まず「次へ」というテキストを含むボタンを探す
                    buttons = self.browser.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        try:
                            if "次へ" in button.text:
                                button.click()
                                logger.info("✓ テキスト内容で「次へ」ボタン（2/3）をクリックしました")
                                next_button_finder = True
                                break
                        except:
                            continue
                    
                    # 2. ダイアログ内の最初のボタンをクリック
                    if not next_button_finder:
                        dialog_buttons = self.browser.driver.find_elements(By.CSS_SELECTOR, "div.ui-dialog-buttonpane button")
                        if dialog_buttons and len(dialog_buttons) > 0:
                            # 通常、2番目のボタンが「次へ」
                            if len(dialog_buttons) >= 2:
                                dialog_buttons[1].click()
                            else:
                                dialog_buttons[0].click()
                            logger.info("✓ ダイアログ内のボタンとして「次へ」ボタン（2/3）をクリックしました")
                            next_button_finder = True
                        else:
                            logger.error("「次へ」ボタン（2/3）が見つかりませんでした")
                            return False
            except Exception as e:
                logger.error(f"「次へ」ボタン（2/3）のクリック中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("next_button_2_error.png")
                return False
            
            # 処理待機
            time.sleep(2)
            
            # 「実行」ボタンをクリック（3/3）
            try:
                logger.info("「実行」ボタンをクリックします")
                if self.browser.click_element('export_dialog', 'execute_button'):
                    logger.info("✓ 「実行」ボタンをクリックしました")
                else:
                    # 直接CSSセレクタまたはXPathを使用した代替手段
                    execute_button_finder = False
                    
                    # 1. まず「実行」というテキストを含むボタンを探す
                    buttons = self.browser.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        try:
                            if "実行" in button.text:
                                button.click()
                                logger.info("✓ テキスト内容で「実行」ボタンをクリックしました")
                                execute_button_finder = True
                                break
                        except:
                            continue
                    
                    # 2. ダイアログ内のボタンを探索
                    if not execute_button_finder:
                        dialog_buttons = self.browser.driver.find_elements(By.CSS_SELECTOR, "div.ui-dialog-buttonpane button")
                        if dialog_buttons and len(dialog_buttons) > 0:
                            # 通常、最後のボタンが「実行」
                            dialog_buttons[-1].click()
                            logger.info("✓ ダイアログ内の最後のボタンとして「実行」ボタンをクリックしました")
                            execute_button_finder = True
                        else:
                            logger.error("「実行」ボタンが見つかりませんでした")
                            return False
            except Exception as e:
                logger.error(f"「実行」ボタンのクリック中にエラーが発生しました: {str(e)}")
                self.browser.save_screenshot("execute_button_error.png")
                return False
            
            # エクスポート完了を待機
            try:
                logger.info("エクスポート完了を待機します")
                time.sleep(3)
                self.browser.save_screenshot("after_execute_button.png")
                
                # 「OK」ボタンが表示される場合はクリック
                try:
                    if self.browser.click_element('export_dialog', 'ok_button'):
                        logger.info("✓ 「OK」ボタンをクリックしました")
                    else:
                        # 直接「OK」テキストを含むボタンを探す
                        buttons = self.browser.driver.find_elements(By.TAG_NAME, "button")
                        for button in buttons:
                            try:
                                if "OK" in button.text or "ok" in button.text.lower():
                                    button.click()
                                    logger.info("✓ テキスト内容で「OK」ボタンをクリックしました")
                                    break
                            except:
                                continue
                except Exception as ok_e:
                    logger.warning(f"「OK」ボタンのクリック中にエラー: {str(ok_e)}")
                
                # ファイルのダウンロードを待機
                logger.info("ファイルのダウンロードを待機します")
                time.sleep(5)  # ダウンロードが完了するまで十分待機
                
                # ダウンロードしたファイルを確認
                self._download_exported_csv()
                
            except Exception as dialog_e:
                logger.error(f"エクスポートダイアログの処理中にエラーが発生しました: {str(dialog_e)}")
                self.browser.save_screenshot("export_dialog_error.png")
                return False
            
            # 処理完了
            logger.info("対応履歴データのエクスポート処理が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"対応履歴データのエクスポート処理中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("export_history_data_error.png")
            return False
    
    def _download_exported_csv(self, max_retries: int = 3, retry_interval: int = 45) -> Optional[str]:
        """
        エクスポートされたCSVファイルをダウンロードする
        
        Args:
            max_retries (int): 最大リトライ回数（デフォルト: 3）
            retry_interval (int): リトライ間隔（秒）（デフォルト: 45）
            
        Returns:
            Optional[str]: ダウンロードされたCSVファイルのパス、失敗した場合はNone
        """
        # エクスポート結果リストを開く
        for attempt in range(max_retries):
            try:
                logger.info(f"エクスポート結果リストを開く（試行 {attempt + 1}/{max_retries}）")
                
                # テキスト要素で「エクスポートの結果一覧を開く」を探す
                logger.info("テキストで「エクスポートの結果一覧を開く」ボタンを探索します")
                export_result_button_found = False
                
                # まずliタグ内のテキストで探す
                elements = self.browser.driver.find_elements(By.TAG_NAME, "li")
                for element in elements:
                    if "エクスポートの結果一覧を開く" in element.text:
                        logger.info(f"「エクスポートの結果一覧を開く」テキストを含む要素を発見しました: {element.text}")
                        element.click()
                        logger.info("✓ テキストで「エクスポートの結果一覧を開く」ボタンをクリックしました")
                        export_result_button_found = True
                        break
                
                # テキストで見つからない場合はタイトル属性で探す
                if not export_result_button_found:
                    logger.info("タイトル属性で「エクスポートの結果一覧を開く」ボタンを探索します")
                    elements = self.browser.driver.find_elements(By.TAG_NAME, "li")
                    for element in elements:
                        try:
                            title = element.get_attribute("title")
                            if title and "エクスポートの結果一覧を開く" in title:
                                logger.info(f"「エクスポートの結果一覧を開く」タイトルを持つ要素を発見しました")
                                element.click()
                                logger.info("✓ タイトル属性で「エクスポートの結果一覧を開く」ボタンをクリックしました")
                                export_result_button_found = True
                                break
                        except:
                            continue
                
                # タイトル属性でも見つからない場合はクラス名で探す
                if not export_result_button_found:
                    logger.info("クラス名で「エクスポートの結果一覧を開く」ボタンを探索します")
                    elements = self.browser.driver.find_elements(By.CLASS_NAME, "p-notificationbar-item-export")
                    if elements:
                        logger.info("クラス名で「エクスポートの結果一覧を開く」ボタンを発見しました")
                        elements[0].click()
                        logger.info("✓ クラス名で「エクスポートの結果一覧を開く」ボタンをクリックしました")
                        export_result_button_found = True
                
                # 最後にセレクタを使用して探す
                if not export_result_button_found:
                    logger.info("セレクタで「エクスポートの結果一覧を開く」ボタンを探索します")
                    if self.browser.click_element('export_result', 'result_list_button'):
                        logger.info("✓ セレクタで「エクスポートの結果一覧を開く」ボタンをクリックしました")
                        export_result_button_found = True
                
                if not export_result_button_found:
                    raise Exception("「エクスポートの結果一覧を開く」ボタンが見つかりませんでした")
                
                time.sleep(3)  # リストが表示されるまで待機
                break
            except Exception as e:
                logger.warning(f"エクスポート結果リストを開く際にエラーが発生しました: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"{retry_interval}秒後にリトライします")
                    time.sleep(retry_interval)
                else:
                    logger.error("エクスポート結果リストを開くのを諦めます")
                    return None
    
        
        # CSVダウンロードリンクをクリック
        for attempt in range(max_retries):
            try:
                logger.info(f"CSVダウンロードリンクをクリック（試行 {attempt + 1}/{max_retries}）")
                
                # セレクタを使用してCSVダウンロードリンクをクリック
                if not self.browser.click_element('export_result', 'csv_download_link'):
                    logger.warning("セレクタでCSVダウンロードリンクを見つけられませんでした")
                    
                    # テキストでリンクを探す
                    try:
                        logger.info("テキストでCSVダウンロードリンクを探索します")
                        links = self.browser.driver.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            link_text = link.text.strip()
                            if "エクスポートしたデーターを取得する" in link_text:
                                logger.info(f"「エクスポートしたデーターを取得する」テキストを含むリンクを発見しました: {link_text}")
                                link.click()
                                logger.info("✓ テキストでCSVダウンロードリンクをクリックしました")
                                break
                            elif "CSV" in link_text:
                                logger.info(f"「CSV」テキストを含むリンクを発見しました: {link_text}")
                                link.click()
                                logger.info("✓ テキストでCSVダウンロードリンクをクリックしました")
                                break
                        else:
                            # href属性で探す
                            links = self.browser.driver.find_elements(By.CSS_SELECTOR, "a[href*='download']")
                            if links:
                                logger.info("href属性でCSVダウンロードリンクを発見しました")
                                links[0].click()
                                logger.info("✓ href属性でCSVダウンロードリンクをクリックしました")
                            else:
                                raise Exception("CSVダウンロードリンクが見つかりませんでした")
                    except Exception as e:
                        raise e
                
                # ダウンロードが完了するまで待機
                logger.info("CSVファイルのダウンロードを待機中...")
                time.sleep(10)  # ダウンロード開始のための初期待機
                
                # ダウンロードディレクトリで新しいCSVファイルを待機
                csv_path = find_latest_csv_in_downloads()
                if csv_path:
                    logger.info(f"CSVファイルのダウンロードが完了しました: {csv_path}")
                    return csv_path
                else:
                    logger.warning("CSVファイルのダウンロードを検出できませんでした")
                    if attempt < max_retries - 1:
                        logger.info(f"{retry_interval}秒後にリトライします")
                        time.sleep(retry_interval)
                    else:
                        # 最終試行でも失敗した場合は、最新のCSVファイルを探す
                        latest_csv = find_latest_csv_in_downloads()
                        if latest_csv:
                            logger.info(f"最新のCSVファイルを使用します: {latest_csv}")
                            return latest_csv
                        logger.error("CSVファイルをダウンロードできませんでした")
                        return None
            except Exception as e:
                logger.warning(f"CSVダウンロード中にエラーが発生しました: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"{retry_interval}秒後にリトライします")
                    time.sleep(retry_interval)
                else:
                    logger.error("CSVファイルをダウンロードできませんでした")
                    return None
    
    def _verify_logout(self):
        """
        ログアウトが正常に完了したかを確認する
        
        Returns:
            bool: ログアウトが成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # ログイン画面に戻ったことを確認
            login_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if login_elements:
                logger.info("ログイン画面に戻ったことを確認しました")
                logger.info("✅ ログアウト処理が完了しました")
                return True
            else:
                # URLでログアウトを確認
                current_url = self.browser.driver.current_url
                logger.info(f"現在のURL: {current_url}")
                if "login" in current_url or "auth" in current_url:
                    logger.info("ログインページのURLを確認しました")
                    logger.info("✅ ログアウト処理が完了しました")
                    return True
                else:
                    logger.warning("ログイン画面への遷移が確認できませんでした")
                    return False
        except Exception as e:
            logger.warning(f"ログイン画面確認中にエラーが発生しました: {str(e)}")
            return False
    
    def execute_common_history_flow(self):
        """
        対応履歴関連の共通処理フローを実行する
        
        以下の処理を順番に実行します：
        1. 「その他業務」ボタンをクリックして新しいウィンドウを開く
        2. 対応履歴メニューをクリック
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 対応履歴関連の共通処理フローを開始します ===")
            
            # 「その他業務」ボタンをクリック
            if not self.click_other_operations_button():
                logger.error("「その他業務」ボタンのクリック処理に失敗しました")
                return False
            
            # 対応履歴メニューをクリック
            if not self.click_history_menu():
                logger.error("対応履歴メニューのクリック処理に失敗しました")
                return False
            
            logger.info("✅ 対応履歴関連の共通処理フローが正常に完了しました")
            return True
            
        except Exception as e:
            logger.error(f"対応履歴関連の共通処理フロー中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("common_history_flow_error.png")
            return False
    
    def execute_operations_flow(self):
        """
        業務操作フローを実行する
        
        以下の処理を順番に実行します：
        1. 対応履歴関連の共通処理フロー（「その他業務」ボタンクリック、対応履歴メニュークリック）
        2. 「すべての対応履歴」リンクをクリック
        3. 「全てチェック」チェックボックスをクリック
        4. 「もっと見る」ボタンを繰り返しクリックして、すべての対応履歴を表示
        5. 対応履歴データのエクスポート処理を実行
        
        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.info("=== 業務操作フローを開始します ===")
            
            # 対応履歴関連の共通処理フローを実行
            if not self.execute_common_history_flow():
                logger.error("対応履歴関連の共通処理フローに失敗しました")
                return False
            
            # 「すべての対応履歴」リンクをクリック
            if not self.click_all_history():
                logger.error("「すべての対応履歴」リンクのクリック処理に失敗しました")
                return False
            
            # 対応履歴一覧画面で「全てチェック」チェックボックスをクリック
            if not self.select_all_correspondence():
                logger.warning("「全てチェック」チェックボックスのクリックに失敗しましたが、処理を継続します")
                # フェイルセーフとして、単一行のチェックを試す処理をここに追加することも可能
            
            # 「もっと見る」ボタンを繰り返しクリックして、すべての対応履歴を表示
            if not self.click_show_more_repeatedly():
                logger.error("「もっと見る」ボタンの繰り返しクリック処理に失敗しました")
                return False
            
            # 対応履歴データのエクスポート処理を実行
            if not self.export_history_data():
                logger.error("対応履歴データのエクスポート処理に失敗しました")
                return False
            
            logger.info("✅ 業務操作フローが正常に完了しました")
            return True
            
        except Exception as e:
            logger.error(f"業務操作フロー中にエラーが発生しました: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser.save_screenshot("operations_flow_error.png")
            return False