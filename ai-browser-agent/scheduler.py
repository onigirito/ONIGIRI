"""
自動スケジューラー＆ジョブウォッチャー
- 定期実行タスクの自動トリガー
- ジョブ完了監視→AI判断→次アクション実行
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

import requests
import yaml

from ai_decider import AIDecider


class TaskScheduler:
    """タスク自動実行スケジューラー"""

    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base = api_base_url
        self.last_run: Dict[str, float] = {}

    async def run_scheduler_loop(self):
        """自動実行タスクを定期的にトリガー"""
        print("🕐 Scheduler started")

        while True:
            try:
                # タスク定義を取得
                buttons = requests.get(f"{self.api_base}/buttons").json()

                for button in buttons:
                    if not button.get("auto"):
                        continue

                    interval = button.get("interval_sec", 3600)
                    task_name = button["name"]

                    # 前回実行からの経過時間をチェック
                    last_time = self.last_run.get(task_name, 0)
                    elapsed = time.time() - last_time

                    if elapsed >= interval:
                        print(f"⏰ Auto-triggering: {task_name}")
                        response = requests.post(f"{self.api_base}/run/{task_name}")
                        if response.status_code == 200:
                            self.last_run[task_name] = time.time()
                            print(f"  ✓ Job created: {response.json()['job_id']}")

            except Exception as e:
                print(f"❌ Scheduler error: {e}")

            await asyncio.sleep(30)  # 30秒ごとにチェック


class JobWatcher:
    """ジョブ完了を監視してAI判断を実行"""

    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base = api_base_url
        self.processed_jobs: Set[str] = set()
        self.ai_decider = AIDecider()

    async def run_watcher_loop(self):
        """完了ジョブを監視してAIに判断させる"""
        print("👁️  Job Watcher started")

        while True:
            try:
                # DONE状態のジョブを取得
                done_jobs = requests.get(
                    f"{self.api_base}/jobs", params={"status": "DONE"}
                ).json()

                for job in done_jobs:
                    job_id = job["job_id"]

                    # 既に処理済みならスキップ
                    if job_id in self.processed_jobs:
                        continue

                    print(f"\n📋 New completed job: {job_id} ({job['task_name']})")
                    await self._handle_completed_job(job)
                    self.processed_jobs.add(job_id)

            except Exception as e:
                print(f"❌ Watcher error: {e}")

            await asyncio.sleep(10)  # 10秒ごとにチェック

    async def _handle_completed_job(self, job: dict):
        """完了ジョブをAIに渡して次アクションを決定"""
        try:
            # コンテキスト情報を収集
            risk_limits = requests.get(f"{self.api_base}/risk_limits").json()
            buttons_list = requests.get(f"{self.api_base}/buttons").json()
            available_buttons = [b["name"] for b in buttons_list]

            context = {
                "balance": 1200000,  # TODO: 実際の残高取得
                "daily_pnl": 0,  # TODO: 実際のP/L取得
                "max_loss_per_day": risk_limits.get("max_loss_per_day", 20000),
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 結果サマリーを作成
            result = job.get("result", {})
            if result.get("success"):
                summary = str(result.get("result", "Success"))[:500]
            else:
                summary = f"ERROR: {result.get('error', 'Unknown error')}"

            # AIに判断を依頼
            print(f"🤖 Asking AI for next action...")
            decision = self.ai_decider.decide_next_action(
                finished_task=job["task_name"],
                result_summary=summary,
                available_buttons=available_buttons,
                context=context,
            )

            print(f"💡 AI Decision: {decision.decision_type}")
            print(f"   Reason: {decision.reason}")

            # 決定に基づいてアクション実行
            if decision.decision_type == "run_button":
                button_name = decision.button_name
                print(f"▶️  Executing button: {button_name}")
                response = requests.post(f"{self.api_base}/run/{button_name}")
                if response.status_code == 200:
                    new_job_id = response.json()["job_id"]
                    print(f"   ✓ New job created: {new_job_id}")

            elif decision.decision_type == "create_button":
                print(f"🆕 AI suggests creating new button:")
                print(f"   Spec: {decision.new_button_spec}")
                # TODO: 人間の承認プロセス

            elif decision.decision_type == "alert":
                print(f"⚠️  ALERT: {decision.alert_message}")
                # TODO: 通知システム連携

            elif decision.decision_type == "wait":
                print(f"⏸️  Waiting (no action needed)")

        except Exception as e:
            print(f"❌ Error handling job: {e}")


async def main():
    """メインループ：スケジューラーとウォッチャーを並行実行"""
    scheduler = TaskScheduler()
    watcher = JobWatcher()

    print("=" * 60)
    print("🚀 AI Browser Agent - Scheduler & Watcher")
    print("=" * 60)

    # 両方を並行実行
    await asyncio.gather(
        scheduler.run_scheduler_loop(),
        watcher.run_watcher_loop(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested")
