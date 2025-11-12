"""
AI判断システム
ジョブ完了後に状況を分析し、次のアクションを決定する
"""
import json
import os
from typing import Dict, Literal, Optional

from anthropic import Anthropic
from pydantic import BaseModel


class AIDecision(BaseModel):
    """AI判断結果"""

    decision_type: Literal["run_button", "create_button", "wait", "alert"]
    button_name: Optional[str] = None
    reason: str
    # create_button の場合
    new_button_spec: Optional[Dict] = None
    # alert の場合
    alert_message: Optional[str] = None


class AIDecider:
    """AIによる次アクション判断"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def decide_next_action(
        self,
        finished_task: str,
        result_summary: str,
        available_buttons: list,
        context: dict,
    ) -> AIDecision:
        """
        完了したタスクの結果を受けて、次のアクションを決定

        Args:
            finished_task: 完了したタスク名
            result_summary: タスク実行結果の要約
            available_buttons: 利用可能なボタン一覧
            context: 現在のコンテキスト（残高、リスク制限など）
        """
        prompt = self._build_prompt(
            finished_task, result_summary, available_buttons, context
        )

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.2,
            system=self._get_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )

        # レスポンスをパース
        content = response.content[0].text
        try:
            decision_data = json.loads(content)
            return AIDecision(**decision_data)
        except json.JSONDecodeError:
            # JSONパースに失敗した場合はwaitとして扱う
            return AIDecision(
                decision_type="wait",
                reason=f"AI response parsing failed: {content[:200]}",
            )

    def _get_system_prompt(self) -> str:
        return """あなたはAIブラウザエージェントの判断システムです。

タスク実行完了後、次に取るべきアクションを決定してください。

選択肢:
1. run_button: 既存のボタン（タスク）を実行
2. create_button: 新しいタスクが必要な場合、その仕様を提案
3. wait: 何もせず待機
4. alert: 人間の注意・判断が必要な状況

リスク管理の原則:
- 損失が制限に近づいている場合は慎重に
- テストトレード結果が異常な場合はアラート
- 市場の急変時は人間の判断を仰ぐ
- 新しいボタン作成は本当に必要な時のみ

必ずJSON形式で返してください:
{
  "decision_type": "run_button" | "create_button" | "wait" | "alert",
  "button_name": "実行するボタン名（run_buttonの場合）",
  "reason": "判断理由",
  "new_button_spec": { ... }  // create_buttonの場合のみ
  "alert_message": "..."  // alertの場合のみ
}"""

    def _build_prompt(
        self, finished_task: str, result_summary: str, available_buttons: list, context: dict
    ) -> str:
        return f"""完了したタスク: {finished_task}

実行結果:
{result_summary}

現在の状況:
- 利用可能なボタン: {', '.join(available_buttons)}
- 残高: {context.get('balance', 'N/A')}円
- 本日の損益: {context.get('daily_pnl', 'N/A')}円
- 最大許容損失: {context.get('max_loss_per_day', 'N/A')}円
- 現在時刻: {context.get('current_time', 'N/A')}

次に取るべきアクションを決定してください。"""


def test_ai_decider():
    """テスト実行"""
    decider = AIDecider()

    # テストケース: 市場スキャン完了
    decision = decider.decide_next_action(
        finished_task="scan_market",
        result_summary="日経平均 -1.2%, TOPIX -0.9%, ボラティリティ上昇",
        available_buttons=["scan_market", "test_trade", "analyze_portfolio"],
        context={
            "balance": 1200000,
            "daily_pnl": -5000,
            "max_loss_per_day": 20000,
            "current_time": "2025-11-12 10:30:00",
        },
    )

    print("AI Decision:")
    print(json.dumps(decision.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_ai_decider()
