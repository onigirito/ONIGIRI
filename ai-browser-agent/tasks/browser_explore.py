"""
ブラウザ探索タスク
ブラウザUIを解析して構造・ボタン配置を理解
"""
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from browser_agent import BrowserAgent


def main(target_url: str = "https://example.com"):
    """
    ブラウザUIを探索して構造を学習

    Args:
        target_url: 探索対象のURL
    """
    print(f"🔍 Exploring browser UI: {target_url}")

    agent = BrowserAgent(headless=True)

    try:
        agent.start()
        agent.navigate(target_url)

        # ページ構造を解析
        structure = agent.analyze_page_structure()

        # スクリーンショット撮影
        screenshot_path = agent.screenshot("explore_result")

        # UI定義を保存
        ui_definition = {
            "url_pattern": target_url,
            "discovered_at": structure.get("timestamp", ""),
            "page_title": structure["title"],
            "clickable_elements": structure["clickables"],
            "input_elements": structure["inputs"],
            "screenshot": str(screenshot_path),
        }

        # ファイルに保存
        output_file = Path("browser_sessions/ui_definition.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ui_definition, f, indent=2, ensure_ascii=False)

        print(f"✓ UI exploration complete:")
        print(f"  - Found {len(structure['clickables'])} clickable elements")
        print(f"  - Found {len(structure['inputs'])} input fields")
        print(f"  - Saved definition to: {output_file}")

        return ui_definition

    finally:
        agent.close()


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    result = main(url)
