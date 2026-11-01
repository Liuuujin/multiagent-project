"""
启动多智能体软件开发系统 Web 服务。

用法:
    python -m multiagent.run            # 默认端口 8080
    python -m multiagent.run --port 9000
"""
from __future__ import annotations

import argparse
import os
import sys

# 确保能 import 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiagent.core.config import load_env

load_env()  # 先加载 .env,后续模块读环境变量才是最新值

from multiagent.core.llm import get_llm  # noqa: E402
from multiagent.web.server import create_app  # noqa: E402


def _report_llm():
    """启动时打印当前用哪个模型,并做一次连通性检查。"""
    try:
        llm = get_llm()
    except Exception as exc:  # noqa: BLE001
        print(f"[警告] LLM 初始化失败: {exc}")
        print("       检查 .env 里的 LLM_PROVIDER / OLLAMA_* 配置")
        return
    name = type(llm).__name__
    detail = getattr(llm, "model", None)
    print(f"LLM: {name}" + (f" ({llm.base_url} / {detail})" if detail else ""))
    if hasattr(llm, "ensure_available"):
        try:
            llm.ensure_available()
            print(f"Ollama 就绪,模型 {detail} 可用")
        except Exception as exc:  # noqa: BLE001
            print(f"[警告] {exc}")


def main():
    parser = argparse.ArgumentParser(description="多智能体软件开发系统")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    load_env()
    _report_llm()

    app = create_app()
    print(f"多智能体系统启动: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
