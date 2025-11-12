"""
ブラウザエージェント - Playwright ベース
ブラウザUIの構造理解・操作を担当
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright, Page, Browser


class BrowserAgent:
    """ブラウザ自動操作エージェント"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.session_dir = Path("browser_sessions")
        self.session_dir.mkdir(exist_ok=True)

    def start(self):
        """ブラウザセッション開始"""
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
            print("🌐 Browser session started")

    def close(self):
        """ブラウザセッション終了"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("🌐 Browser session closed")

    def navigate(self, url: str):
        """ページ遷移"""
        if not self.page:
            self.start()
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        print(f"📄 Navigated to: {url}")

    def screenshot(self, name: str = "screenshot") -> Path:
        """スクリーンショット撮影"""
        if not self.page:
            raise RuntimeError("Browser not started")

        path = self.session_dir / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def analyze_page_structure(self) -> Dict:
        """
        ページ構造を解析
        - クリック可能要素（ボタン、リンク）
        - 入力フォーム
        - テキストコンテンツ
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        # 基本情報
        url = self.page.url
        title = self.page.title()

        # クリック可能要素を抽出
        clickables = self._extract_clickable_elements()

        # フォーム入力要素を抽出
        inputs = self._extract_input_elements()

        # 主要テキストを抽出
        text_content = self.page.inner_text("body")[:2000]

        structure = {
            "url": url,
            "title": title,
            "clickables": clickables,
            "inputs": inputs,
            "text_preview": text_content,
        }

        return structure

    def _extract_clickable_elements(self) -> List[Dict]:
        """クリック可能な要素を抽出"""
        clickables = []

        # ボタン
        buttons = self.page.locator("button, [role='button']").all()
        for i, btn in enumerate(buttons[:20]):  # 最大20個
            try:
                text = btn.inner_text()[:50]
                if text.strip():
                    clickables.append({
                        "id": f"btn_{i}",
                        "type": "button",
                        "text": text,
                        "selector": f"button:nth-of-type({i+1})"
                    })
            except:
                pass

        # リンク
        links = self.page.locator("a").all()
        for i, link in enumerate(links[:20]):
            try:
                text = link.inner_text()[:50]
                href = link.get_attribute("href")
                if text.strip():
                    clickables.append({
                        "id": f"link_{i}",
                        "type": "link",
                        "text": text,
                        "href": href,
                        "selector": f"a:nth-of-type({i+1})"
                    })
            except:
                pass

        return clickables

    def _extract_input_elements(self) -> List[Dict]:
        """入力フォーム要素を抽出"""
        inputs = []

        input_elements = self.page.locator("input, textarea, select").all()
        for i, elem in enumerate(input_elements[:15]):
            try:
                tag = elem.evaluate("el => el.tagName").lower()
                input_type = elem.get_attribute("type") or "text"
                name = elem.get_attribute("name") or f"input_{i}"
                placeholder = elem.get_attribute("placeholder") or ""

                inputs.append({
                    "id": f"input_{i}",
                    "tag": tag,
                    "type": input_type,
                    "name": name,
                    "placeholder": placeholder,
                    "selector": f"{tag}:nth-of-type({i+1})"
                })
            except:
                pass

        return inputs

    def click_element(self, selector: str):
        """要素をクリック"""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.click(selector, timeout=5000)
        print(f"🖱️  Clicked: {selector}")

    def fill_input(self, selector: str, value: str):
        """入力欄に値を入力"""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.fill(selector, value, timeout=5000)
        print(f"⌨️  Filled '{selector}' with: {value}")

    def wait_for_text(self, text: str, timeout: int = 10000):
        """特定テキストが表示されるまで待機"""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.wait_for_selector(f"text={text}", timeout=timeout)
        print(f"👀 Found text: {text}")


def test_browser_agent():
    """テスト実行"""
    agent = BrowserAgent(headless=False)

    try:
        agent.start()

        # テストサイトにアクセス
        agent.navigate("https://example.com")

        # ページ構造を解析
        structure = agent.analyze_page_structure()
        print("\n📊 Page Structure:")
        print(json.dumps(structure, indent=2, ensure_ascii=False))

        # スクリーンショット
        screenshot_path = agent.screenshot("example_page")
        print(f"\n📸 Screenshot saved: {screenshot_path}")

    finally:
        agent.close()


if __name__ == "__main__":
    test_browser_agent()
