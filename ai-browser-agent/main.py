"""
AIブラウザエージェント - メインFastAPIアプリケーション
ローカルタスクを実行可能な「ボタン」として提供
"""
import asyncio
import importlib
import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Literal

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AI Browser Agent API")

# CORS設定（ローカル用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル状態
TASKS_CONFIG = {}
JOBS: Dict[str, dict] = {}
JOBS_FILE = Path("jobs.json")

# モデル定義
class JobStatus(BaseModel):
    job_id: str
    task_name: str
    status: Literal["PENDING", "RUNNING", "DONE", "ERROR"]
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class RunTaskResponse(BaseModel):
    job_id: str
    task_name: str
    status: str


class ButtonDefinition(BaseModel):
    name: str
    type: Literal["python_module", "shell"]
    module: Optional[str] = None
    command: Optional[str] = None
    auto: bool = False
    interval_sec: Optional[int] = None
    description: str


def load_tasks_config():
    """タスク設定をYAMLから読み込み"""
    global TASKS_CONFIG
    with open("tasks.yaml", "r", encoding="utf-8") as f:
        TASKS_CONFIG = yaml.safe_load(f)


def save_jobs():
    """ジョブ状態を保存"""
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(JOBS, f, indent=2, ensure_ascii=False)


def load_jobs():
    """ジョブ状態を読み込み"""
    global JOBS
    if JOBS_FILE.exists():
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            JOBS = json.load(f)


def _run_python_module(module_spec: str) -> dict:
    """Pythonモジュールを実行"""
    try:
        mod_name, func_name = module_spec.split(":")
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        result = func()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_shell(cmd: str) -> dict:
    """シェルコマンドを実行"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def execute_task(job_id: str, task_name: str):
    """タスクを非同期実行"""
    task_conf = TASKS_CONFIG["tasks"][task_name]

    JOBS[job_id]["status"] = "RUNNING"
    JOBS[job_id]["started_at"] = datetime.now().isoformat()
    save_jobs()

    try:
        if task_conf["type"] == "python_module":
            result = await asyncio.to_thread(_run_python_module, task_conf["module"])
        elif task_conf["type"] == "shell":
            result = await asyncio.to_thread(_run_shell, task_conf["command"])
        else:
            raise ValueError(f"Unknown task type: {task_conf['type']}")

        JOBS[job_id]["status"] = "DONE"
        JOBS[job_id]["result"] = result
    except Exception as e:
        JOBS[job_id]["status"] = "ERROR"
        JOBS[job_id]["error"] = str(e)

    JOBS[job_id]["finished_at"] = datetime.now().isoformat()
    save_jobs()


@app.on_event("startup")
async def startup_event():
    """起動時の初期化"""
    load_tasks_config()
    load_jobs()
    print("🚀 AI Browser Agent API Started")
    print(f"📋 Loaded {len(TASKS_CONFIG.get('tasks', {}))} tasks")


@app.get("/")
def root():
    """ヘルスチェック"""
    return {
        "status": "running",
        "service": "AI Browser Agent",
        "tasks_count": len(TASKS_CONFIG.get("tasks", {})),
        "active_jobs": len([j for j in JOBS.values() if j["status"] == "RUNNING"]),
    }


@app.get("/buttons", response_model=List[ButtonDefinition])
def list_buttons():
    """登録済みボタン（タスク）一覧を取得"""
    buttons = []
    for name, conf in TASKS_CONFIG.get("tasks", {}).items():
        buttons.append(
            ButtonDefinition(
                name=name,
                type=conf["type"],
                module=conf.get("module"),
                command=conf.get("command"),
                auto=conf.get("auto", False),
                interval_sec=conf.get("interval_sec"),
                description=conf.get("description", ""),
            )
        )
    return buttons


@app.post("/run/{task_name}", response_model=RunTaskResponse)
async def run_task(task_name: str):
    """タスクを実行（非同期ジョブとして登録）"""
    if task_name not in TASKS_CONFIG.get("tasks", {}):
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

    job_id = f"job-{uuid.uuid4().hex[:8]}"

    JOBS[job_id] = {
        "job_id": job_id,
        "task_name": task_name,
        "status": "PENDING",
        "created_at": datetime.now().isoformat(),
    }
    save_jobs()

    # バックグラウンドで実行
    asyncio.create_task(execute_task(job_id, task_name))

    return RunTaskResponse(job_id=job_id, task_name=task_name, status="PENDING")


@app.get("/status/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    """ジョブのステータスを取得"""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return JobStatus(**JOBS[job_id])


@app.get("/jobs", response_model=List[JobStatus])
def list_jobs(status: Optional[str] = None):
    """ジョブ一覧を取得"""
    jobs = list(JOBS.values())
    if status:
        jobs = [j for j in jobs if j["status"] == status.upper()]
    return [JobStatus(**j) for j in jobs]


@app.post("/define_button")
async def define_button(button: ButtonDefinition):
    """新しいボタン（タスク）を動的に定義"""
    if button.name in TASKS_CONFIG.get("tasks", {}):
        raise HTTPException(
            status_code=400, detail=f"Task '{button.name}' already exists"
        )

    # tasks.yamlに追加
    if "tasks" not in TASKS_CONFIG:
        TASKS_CONFIG["tasks"] = {}

    TASKS_CONFIG["tasks"][button.name] = {
        "type": button.type,
        "module": button.module,
        "command": button.command,
        "auto": button.auto,
        "interval_sec": button.interval_sec,
        "description": button.description,
    }

    # YAMLファイルに保存
    with open("tasks.yaml", "w", encoding="utf-8") as f:
        yaml.dump(TASKS_CONFIG, f, allow_unicode=True, default_flow_style=False)

    return {"status": "ok", "message": f"Button '{button.name}' created"}


@app.get("/risk_limits")
def get_risk_limits():
    """リスク管理設定を取得"""
    return TASKS_CONFIG.get("risk_limits", {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
