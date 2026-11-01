"""
LLM 抽象层
==========
提供统一的 LLM 接口。当前支持:
- MockLLM: 模拟 LLM,用规则/模板生成确定性输出,用于跑通流程(无需 API key)
- OllamaLLM: 本地 Ollama 原生接口(默认 qwen2.5:3b),无需 API key、无需 openai 包
- OpenAILLM: 真实模型接入(OpenAI 兼容接口,可配置 base_url 支持 DeepSeek/Qwen 等)

通过环境变量切换(也可写在项目根目录的 .env 里):
    LLM_PROVIDER=mock|ollama|openai
    OLLAMA_BASE_URL=...   (默认 http://127.0.0.1:11434)
    OLLAMA_MODEL=...      (默认 qwen2.5:3b)
    OPENAI_API_KEY=...
    OPENAI_BASE_URL=...   (可选,默认 https://api.openai.com/v1)
    OPENAI_MODEL=...      (默认 gpt-4o-mini)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .config import get_float, get_int, load_env


# ---------------------------------------------------------------------------
# 统一消息结构
# ---------------------------------------------------------------------------
@dataclass
class LLMMessage:
    role: str          # "system" | "user" | "assistant"
    content: str
    name: Optional[str] = None   # agent 名,用于可视化


@dataclass
class LLMResult:
    content: str
    raw: Any = None
    usage: Optional[Dict[str, int]] = None


class BaseLLM:
    """所有 LLM 实现的基类。"""

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        raise NotImplementedError

    def complete(self, prompt: str, **kwargs) -> LLMResult:
        return self.chat([LLMMessage(role="user", content=prompt)], **kwargs)


# ---------------------------------------------------------------------------
# MockLLM —— 模拟模型,无需 API key,用于跑通流程
# ---------------------------------------------------------------------------
class MockLLM(BaseLLM):
    """
    模拟 LLM。根据 agent 角色和任务类型,用模板生成看起来合理的输出。
    这样可以在没有真实模型的情况下完整演示多智能体协作流程。
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        # 取最后一条 user 消息作为输入
        user_msg = next((m for m in reversed(messages) if m.role == "user"), None)
        system_msg = next((m for m in messages if m.role == "system"), None)
        content = user_msg.content if user_msg else ""
        system = system_msg.content if system_msg else ""

        # 根据 system 提示中的角色关键词生成对应输出
        role = self._detect_role(system)
        output = self._generate(role, content, system)
        return LLMResult(content=output, usage={"prompt_tokens": len(content), "completion_tokens": len(output)})

    # -- 内部工具 ----------------------------------------------------------
    def _detect_role(self, system: str) -> str:
        s = system.lower()
        # 注意顺序: "测试工程师" 同时含 "测试" 和 "工程师",必须先匹配更具体的
        if "产品经理" in s or "product manager" in s:
            return "pm"
        if "架构师" in s or "architect" in s:
            return "architect"
        if "测试" in s or "tester" in s or "qa" in s:
            return "tester"
        if "审查" in s or "reviewer" in s or "code review" in s:
            return "reviewer"
        if "开发者" in s or "developer" in s or "工程师" in s:
            return "developer"
        return "generic"

    def _generate(self, role: str, content: str, system: str) -> str:
        task = content.strip()
        if role == "pm":
            return self._pm(task)
        if role == "architect":
            return self._architect(task)
        if role == "developer":
            return self._developer(task)
        if role == "tester":
            return self._tester(task)
        if role == "reviewer":
            return self._reviewer(task)
        return f"[模拟响应] 收到任务: {task[:200]}"

    def _pm(self, task: str) -> str:
        return (
            "【产品经理分析】\n"
            f"需求理解: {task[:120]}\n"
            "拆解为以下子任务:\n"
            "1. 定义功能模块与接口\n"
            "2. 设计数据模型\n"
            "3. 实现核心逻辑\n"
            "4. 编写单元测试\n"
            "5. 代码审查与质量把关\n"
            "验收标准: 功能可用、测试通过、代码可读。"
        )

    def _architect(self, task: str) -> str:
        return (
            "【架构设计】\n"
            "技术选型: Python + 模块化分层架构\n"
            "模块划分:\n"
            "- core/: 核心业务逻辑\n"
            "- api/: 对外接口层\n"
            "- tests/: 测试套件\n"
            "关键设计决策:\n"
            "1. 使用依赖注入降低耦合\n"
            "2. 接口与实现分离,便于测试\n"
            "3. 错误处理统一封装\n"
            "约束: 保持简单、可扩展、可测试。"
        )

    def _developer(self, task: str) -> str:
        # 尝试从任务中提取"实现 xxx"之类的指令
        m = re.search(r"(?:实现|编写|开发|create|implement)\s*[:：]?\s*([^\n]+)", task, re.I)
        feature = m.group(1).strip() if m else "核心功能"
        return (
            "【开发者实现】\n"
            f"实现功能: {feature}\n"
            "```python\n"
            "def main():\n"
            "    # 根据架构设计实现核心逻辑\n"
            "    print('Hello from multi-agent system')\n"
            "    return True\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
            "```\n"
            "代码已按架构规范编写,包含必要的注释与错误处理。"
        )

    def _tester(self, task: str) -> str:
        return (
            "【测试工程师】\n"
            "编写并运行单元测试:\n"
            "```python\n"
            "def test_main():\n"
            "    assert main() is True\n"
            "```\n"
            "测试结果: 3 个用例全部通过 ✅\n"
            "覆盖情况: 核心逻辑 100%,边界条件已覆盖。"
        )

    def _reviewer(self, task: str) -> str:
        return (
            "【代码审查】\n"
            "审查结论: 通过 ✅\n"
            "优点:\n"
            "- 代码结构清晰,符合架构设计\n"
            "- 命名规范,注释到位\n"
            "- 测试覆盖充分\n"
            "改进建议(可选):\n"
            "- 可进一步补充异常场景测试\n"
            "总体评价: 质量良好,可以合并。"
        )


# ---------------------------------------------------------------------------
# OllamaLLM —— 本地 Ollama 原生接口(/api/chat)
# ---------------------------------------------------------------------------
class OllamaLLM(BaseLLM):
    """
    本地 Ollama 模型。走 Ollama 原生 /api/chat 接口,只依赖 requests,
    不需要 API Key,也不需要安装 openai 包。
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        load_env()
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:3b"
        self.timeout = timeout or get_int("OLLAMA_TIMEOUT", 300)
        self.options: Dict[str, Any] = {
            "temperature": get_float("OLLAMA_TEMPERATURE", 0.6),
            "num_ctx": get_int("OLLAMA_NUM_CTX", 8192),
            "num_predict": get_int("OLLAMA_NUM_PREDICT", 768),
        }
        if options:
            self.options.update(options)

    # -- 可用性检查 --------------------------------------------------------
    def ensure_available(self) -> None:
        """确认 Ollama 服务在跑、模型已下载,否则给出明确报错。"""
        import requests

        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"连不上 Ollama({self.base_url}):{exc}\n"
                f"请先启动 Ollama,并确认 `ollama list` 里有 {self.model}"
            ) from exc

        names = {m.get("name") for m in resp.json().get("models", [])}
        if self.model not in names and f"{self.model}:latest" not in names:
            raise RuntimeError(
                f"Ollama 中找不到模型 {self.model}。已安装:{sorted(names) or '无'}\n"
                f"请先执行:ollama pull {self.model}"
            )

    # -- 调用 --------------------------------------------------------------
    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        import requests

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            # 让模型在内存里多待一会儿,避免每次跑任务都重新加载(3B 冷启动约 20-30s)
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE") or "30m",
            "options": {**self.options, **{k: v for k, v in kwargs.items() if k in
                                           ("temperature", "num_ctx", "num_predict", "top_p", "seed")}},
        }

        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                content = (data.get("message") or {}).get("content", "") or ""
                return LLMResult(
                    content=content.strip(),
                    raw=data,
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == 0:
                    continue
        raise RuntimeError(f"Ollama 调用失败({self.model} @ {self.base_url}):{last_error}")


# ---------------------------------------------------------------------------
# OpenAILLM —— 真实模型接入(OpenAI 兼容)
# ---------------------------------------------------------------------------
class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        load_env()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # 本地兼容端点(如 Ollama 的 /v1)不校验 key,给个占位值即可
        local = any(h in self.base_url for h in ("127.0.0.1", "localhost", "0.0.0.0"))
        if not self.api_key and local:
            self.api_key = "ollama"
        if not self.api_key:
            raise ValueError("OpenAILLM 需要 OPENAI_API_KEY,或使用 MockLLM / OllamaLLM")

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResult:
        """直接走 HTTP /chat/completions,不依赖 openai SDK(云端无需额外装包)。"""
        import requests

        url = self.base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "temperature": kwargs.get("temperature", get_float("OPENAI_TEMPERATURE", 0.6)),
        }
        if kwargs.get("max_tokens"):
            body["max_tokens"] = kwargs["max_tokens"]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = get_int("OPENAI_TIMEOUT", 180)
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"模型接口不可达({self.model} @ {self.base_url}):{exc}")
        if resp.status_code != 200:
            raise RuntimeError(f"模型接口返回 {resp.status_code}({self.model}):{resp.text[:300]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"模型接口无有效返回:{str(data)[:300]}")
        usage = data.get("usage") or {}
        return LLMResult(
            content=(choices[0].get("message") or {}).get("content", "") or "",
            raw=data,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        )


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------
def get_llm() -> BaseLLM:
    load_env()
    provider = (os.getenv("LLM_PROVIDER") or "mock").strip().lower()
    if provider in ("ollama", "local"):
        return OllamaLLM()
    if provider in ("openai", "openai-compatible", "deepseek", "qwen", "dashscope"):
        try:
            return OpenAILLM()
        except ValueError:
            # 未配置 API Key 时降级为模拟模式,保证服务仍可启动
            return MockLLM()
    return MockLLM()


def describe_llm(llm: Optional[BaseLLM] = None) -> Dict[str, Any]:
    """给前端展示用的模型信息(标签 + 是否为模拟输出)。"""
    try:
        llm = llm or get_llm()
    except Exception as exc:  # noqa: BLE001
        return {"provider": "unknown", "model": "-", "label": "模型未配置", "mock": True, "error": str(exc)}
    name = type(llm).__name__
    if isinstance(llm, OllamaLLM):
        return {"provider": "ollama", "model": llm.model, "label": f"本地 Ollama · {llm.model}", "mock": False}
    if isinstance(llm, OpenAILLM):
        return {"provider": "openai", "model": llm.model, "label": f"在线模型 · {llm.model}", "mock": False}
    return {"provider": "mock", "model": name, "label": "演示模式 · 规则模板输出(非真实模型)", "mock": True}
