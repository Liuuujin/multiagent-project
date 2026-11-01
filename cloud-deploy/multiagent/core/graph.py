"""
LangGraph 编排层
================
定义多智能体协作的状态图。流程:

    PM(产品经理) → Architect(架构师) → Developer(开发者) → Tester(测试) → Reviewer(审查)

带反馈循环:
- 测试失败 → 回到 Developer 修复
- 审查不通过 → 回到 Developer 修改

每个节点执行时通过回调把事件推送给 Web 前端(SSE 实时可视化)。
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import StateGraph, END

from .config import get_int, load_env
from .llm import BaseLLM, LLMMessage, get_llm
from ..agents.definitions import get_role


# ---------------------------------------------------------------------------
# 状态定义(使用 TypedDict 作为 LangGraph 状态 schema)
# ---------------------------------------------------------------------------
from typing import TypedDict


class AgentState(TypedDict, total=False):
    task: str
    history: List[Dict[str, str]]
    last_role: Optional[str]
    last_output: str
    iterations: int          # developer 被调用的次数,用于限制反馈循环


# 事件回调类型: (event_type, payload) -> None
EventCallback = Callable[[str, Dict[str, Any]], None]


# ---------------------------------------------------------------------------
# 多智能体图
# ---------------------------------------------------------------------------
class MultiAgentGraph:
    def __init__(self, llm: Optional[BaseLLM] = None, event_callback: Optional[EventCallback] = None,
                 max_iterations: Optional[int] = None):
        load_env()
        self.llm = llm or get_llm()
        self.event_callback = event_callback or (lambda t, p: None)
        self.max_iterations = max_iterations or get_int("MAX_ITERATIONS", 2)
        self._build()

    # -- 事件推送 ----------------------------------------------------------
    def _emit(self, event_type: str, payload: Dict[str, Any]):
        payload["ts"] = time.time()
        self.event_callback(event_type, payload)

    # -- 节点实现 ----------------------------------------------------------
    def _run_agent(self, role_key: str, state: AgentState) -> Dict[str, Any]:
        role = get_role(role_key)
        task = state.get("task", "")
        history = state.get("history", []) or []

        # 构造消息: 系统提示 + 上下文(前序 agent 输出) + 当前任务
        messages = [LLMMessage(role="system", content=role.system_prompt)]
        if history:
            ctx = "\n\n".join(f"[{h['role']}]\n{h['content']}" for h in history)
            # 小模型上下文有限,超出预算时保留最近的产出
            budget = get_int("MAX_CONTEXT_CHARS", 6000)
            if len(ctx) > budget:
                ctx = "……(更早的产出已省略)\n\n" + ctx[-budget:]
            messages.append(LLMMessage(role="user", content=f"以下是前序协作产出,请参考:\n{ctx}"))
        messages.append(LLMMessage(role="user", content=f"当前任务: {task}"))

        # 通知开始
        self._emit("agent_start", {"role": role_key, "name": role.name, "task": task})

        # 调用 LLM
        result = self.llm.chat(messages)
        output = result.content

        # 记录到历史
        history = list(history) + [{"role": role_key, "name": role.name, "content": output}]

        # 通知完成
        self._emit("agent_done", {"role": role_key, "name": role.name, "content": output})

        return {"history": history, "last_role": role_key, "last_output": output}

    # -- 各节点 ------------------------------------------------------------
    def node_pm(self, state: AgentState) -> Dict[str, Any]:
        return self._run_agent("pm", state)

    def node_architect(self, state: AgentState) -> Dict[str, Any]:
        return self._run_agent("architect", state)

    def node_developer(self, state: AgentState) -> Dict[str, Any]:
        result = self._run_agent("developer", state)
        result["iterations"] = int(state.get("iterations") or 0) + 1
        return result

    def node_tester(self, state: AgentState) -> Dict[str, Any]:
        return self._run_agent("tester", state)

    def node_reviewer(self, state: AgentState) -> Dict[str, Any]:
        return self._run_agent("reviewer", state)

    # -- 条件路由 ----------------------------------------------------------
    @staticmethod
    def judge(output: str) -> Optional[bool]:
        """
        从输出中判断结论: True=通过, False=不通过, None=判断不出来。

        优先读「结论: 通过 / 不通过」标记;否则退化为关键词匹配。
        注意「不通过」包含「通过」,必须先判断否定。
        """
        text = output or ""
        marks = re.findall(r"结论\s*[:：]\s*(不通过|通过|未通过|失败|驳回|可以合并|需要修改)", text)
        if marks:
            last = marks[-1]
            return last in ("通过", "可以合并")
        if re.search(r"(不通过|未通过|不予通过|失败|驳回|需要修改)", text):
            return False
        if re.search(r"(通过|✅|可以合并|LGTM)", text, re.I):
            return True
        return None

    def _exhausted(self, state: AgentState) -> bool:
        return int(state.get("iterations") or 0) >= self.max_iterations

    def _stop_due_to_cap(self, reason: str) -> str:
        self._emit("loop_capped", {
            "reason": reason,
            "iterations": self.max_iterations,
            "message": f"已达最大迭代次数 {self.max_iterations},流程终止",
        })
        return END

    def route_after_tester(self, state: AgentState) -> str:
        """测试通过则进入审查,否则回到开发者修复(受迭代上限约束)。"""
        verdict = self.judge(state.get("last_output", ""))
        if verdict is not False:
            return "reviewer"
        if self._exhausted(state):
            return self._stop_due_to_cap("测试未通过")
        return "developer"

    def route_after_reviewer(self, state: AgentState) -> str:
        """审查通过则结束,否则回到开发者修改(受迭代上限约束)。"""
        verdict = self.judge(state.get("last_output", ""))
        if verdict is not False:
            return END
        if self._exhausted(state):
            return self._stop_due_to_cap("代码审查未通过")
        return "developer"

    # -- 构建图 ------------------------------------------------------------
    def _build(self):
        g = StateGraph(AgentState)

        g.add_node("pm", self.node_pm)
        g.add_node("architect", self.node_architect)
        g.add_node("developer", self.node_developer)
        g.add_node("tester", self.node_tester)
        g.add_node("reviewer", self.node_reviewer)

        g.set_entry_point("pm")
        g.add_edge("pm", "architect")
        g.add_edge("architect", "developer")
        g.add_edge("developer", "tester")
        g.add_conditional_edges("tester", self.route_after_tester, {"reviewer": "reviewer", "developer": "developer"})
        g.add_conditional_edges("reviewer", self.route_after_reviewer, {END: END, "developer": "developer"})

        self.graph = g.compile()

    # -- 运行 --------------------------------------------------------------
    def run(self, task: str, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        """运行一次多智能体协作,返回最终状态。"""
        if max_iterations:
            self.max_iterations = max_iterations
        self._emit("run_start", {"task": task})
        state: AgentState = {
            "task": task, "history": [], "last_role": None, "last_output": "", "iterations": 0,
        }
        result = self.graph.invoke(state, {"recursion_limit": 50})
        if result is None:
            result = state
        self._emit("run_end", {"history": result.get("history", [])})
        return result
