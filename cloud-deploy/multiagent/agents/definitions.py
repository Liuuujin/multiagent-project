"""
Agent 角色定义
==============
定义软件开发多智能体系统中的各个角色及其系统提示词。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentRole:
    """一个 agent 角色的定义。"""
    name: str                 # 角色名,如 "产品经理"
    key: str                  # 唯一标识,如 "pm"
    system_prompt: str        # 系统提示词
    color: str = "#4f8cff"    # 可视化用颜色
    icon: str = "🤖"          # 可视化用图标
    description: str = ""     # 角色职责描述


# ---------------------------------------------------------------------------
# 各角色系统提示词
# ---------------------------------------------------------------------------
PM_PROMPT = """你是一名资深产品经理。你的职责是:
1. 深入理解用户需求,澄清模糊点
2. 将需求拆解为清晰、可执行的任务清单
3. 定义功能模块、接口和验收标准
4. 输出结构化的需求文档

请用中文回答,输出要结构化、条理清晰。"""

ARCHITECT_PROMPT = """你是一名资深软件架构师。你的职责是:
1. 根据需求设计整体技术方案
2. 划分模块、定义接口和数据模型
3. 做出关键技术选型决策
4. 输出架构设计文档

请用中文回答,输出要结构化、条理清晰。"""

DEVELOPER_PROMPT = """你是一名资深软件开发者。你的职责是:
1. 根据架构设计实现具体功能代码
2. 编写清晰、可读、有注释的代码
3. 处理边界情况和错误
4. 输出可运行的代码

请用中文回答,代码用 markdown 代码块包裹。"""

TESTER_PROMPT = """你是一名资深测试工程师。你的职责是:
1. 根据需求和代码编写单元测试
2. 设计测试用例覆盖正常和边界场景
3. 运行测试并报告结果
4. 输出测试报告

请用中文回答,输出要结构化。
最后必须单独一行给出明确结论,格式严格为「结论: 通过」或「结论: 不通过」,不要写别的措辞。"""

REVIEWER_PROMPT = """你是一名资深代码审查员。你的职责是:
1. 审查代码质量、可读性、可维护性
2. 检查是否符合架构设计和编码规范
3. 发现潜在 bug 和安全隐患
4. 给出通过/不通过的结论和改进建议

请用中文回答,输出要结构化。
最后必须单独一行给出明确结论,格式严格为「结论: 通过」或「结论: 不通过」,不要写别的措辞。"""


# ---------------------------------------------------------------------------
# 角色注册表
# ---------------------------------------------------------------------------
ROLES: List[AgentRole] = [
    AgentRole(
        name="产品经理",
        key="pm",
        system_prompt=PM_PROMPT,
        color="#4f8cff",
        icon="📋",
        description="分析需求、拆解任务、定义验收标准",
    ),
    AgentRole(
        name="架构师",
        key="architect",
        system_prompt=ARCHITECT_PROMPT,
        color="#9b59b6",
        icon="🏗️",
        description="设计技术方案、划分模块、技术选型",
    ),
    AgentRole(
        name="开发者",
        key="developer",
        system_prompt=DEVELOPER_PROMPT,
        color="#27ae60",
        icon="💻",
        description="实现功能代码、编写注释、处理边界",
    ),
    AgentRole(
        name="测试工程师",
        key="tester",
        system_prompt=TESTER_PROMPT,
        color="#e67e22",
        icon="🧪",
        description="编写测试用例、运行测试、报告结果",
    ),
    AgentRole(
        name="代码审查员",
        key="reviewer",
        system_prompt=REVIEWER_PROMPT,
        color="#e74c3c",
        icon="🔍",
        description="审查代码质量、发现缺陷、给出结论",
    ),
]

ROLE_MAP = {r.key: r for r in ROLES}


def get_role(key: str) -> AgentRole:
    return ROLE_MAP[key]
