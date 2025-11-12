#!/bin/bash
# システム全体のクイックテストスクリプト

echo "==================================="
echo "AI Browser Agent - System Test"
echo "==================================="
echo ""

cd /home/user/ONIGIRI/ai-browser-agent

# 1. タスク単体テスト
echo "1️⃣  Testing individual tasks..."
echo "-----------------------------------"
python3 tasks/scan_market.py
echo ""

# 2. FastAPI起動（バックグラウンド）
echo "2️⃣  Starting FastAPI server..."
echo "-----------------------------------"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
echo "API server started (PID: $API_PID)"
sleep 3
echo ""

# 3. API疎通確認
echo "3️⃣  Testing API endpoints..."
echo "-----------------------------------"
echo "GET /"
curl -s http://127.0.0.1:8000/ | python3 -m json.tool
echo ""

echo "GET /buttons"
curl -s http://127.0.0.1:8000/buttons | python3 -m json.tool | head -20
echo ""

# 4. タスク実行テスト
echo "4️⃣  Running task via API..."
echo "-----------------------------------"
echo "POST /run/scan_market"
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/run/scan_market)
echo $RESPONSE | python3 -m json.tool
JOB_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo ""

# 5. ジョブステータス確認
echo "5️⃣  Checking job status..."
echo "-----------------------------------"
sleep 2
curl -s http://127.0.0.1:8000/status/$JOB_ID | python3 -m json.tool
echo ""

# クリーンアップ
echo "==================================="
echo "Test complete. Cleaning up..."
kill $API_PID
echo "API server stopped"
echo "==================================="
