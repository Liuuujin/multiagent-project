"""
Flask Web 后端
==============
提供:
- GET  /            -> 前端页面
- POST /api/run     -> 提交任务,启动多智能体协作
- GET  /api/events  -> SSE 事件流,实时推送 agent 协作过程
- GET  /api/roles   -> 返回角色定义(供前端展示)
- GET  /api/status  -> 当前运行状态
"""
from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from typing import Dict, List

from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS

from ..core.graph import MultiAgentGraph
from ..core.llm import get_llm, describe_llm
from ..agents.definitions import ROLES

app = Flask(__name__, static_folder="../static", static_url_path="/static")
CORS(app)

# 全局事件队列(SSE 用)
_event_queues: Dict[str, queue.Queue] = {}
_lock = threading.Lock()

# 当前运行状态
_run_state = {
    "running": False,
    "task": "",
    "history": [],
    "started_at": None,
    "finished_at": None,
}


def _broadcast(event_type: str, payload: Dict):
    """把事件推送到所有订阅的 SSE 客户端。"""
    data = json.dumps({"type": event_type, "data": payload}, ensure_ascii=False)
    with _lock:
        for q in list(_event_queues.values()):
            q.put(data)


def _event_callback(event_type: str, payload: Dict):
    _broadcast(event_type, payload)
    # 同步更新运行状态
    if event_type == "run_start":
        _run_state["running"] = True
        _run_state["task"] = payload.get("task", "")
        _run_state["history"] = []
        _run_state["started_at"] = time.time()
        _run_state["finished_at"] = None
    elif event_type == "agent_done":
        _run_state["history"].append({
            "role": payload.get("role"),
            "name": payload.get("name"),
            "content": payload.get("content"),
        })
    elif event_type == "run_end":
        _run_state["running"] = False
        _run_state["finished_at"] = time.time()


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/roles")
def api_roles():
    return jsonify([{
        "key": r.key, "name": r.name, "color": r.color,
        "icon": r.icon, "description": r.description,
    } for r in ROLES])


@app.route("/api/config")
def api_config():
    """返回当前模型配置,供前端展示(避免把模拟输出误认为真实模型生成)。"""
    return jsonify(describe_llm())


@app.route("/api/status")
def api_status():
    return jsonify(_run_state)


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json(force=True) or {}
    task = (data.get("task") or "").strip()
    if not task:
        return jsonify({"error": "任务不能为空"}), 400
    if _run_state["running"]:
        return jsonify({"error": "已有任务在运行中"}), 409

    # 在后台线程运行多智能体协作
    def worker():
        try:
            graph = MultiAgentGraph(llm=get_llm(), event_callback=_event_callback)
            graph.run(task)
        except Exception as e:  # noqa
            _broadcast("error", {"message": str(e)})
            _run_state["running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "任务已启动"})


@app.route("/api/events")
def api_events():
    """SSE 事件流。"""
    client_id = str(uuid.uuid4())
    q = queue.Queue()
    with _lock:
        _event_queues[client_id] = q

    def gen():
        try:
            # 先推送当前状态(重连时恢复)
            yield f"data: {json.dumps({'type': 'snapshot', 'data': _run_state}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    data = q.get(timeout=15)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _lock:
                _event_queues.pop(client_id, None)

    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


def create_app():
    return app
