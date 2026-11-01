# 多智能体软件开发系统（Multi-Agent Software Development System）

基于 **LangGraph** 编排的多智能体协作系统：由「产品经理 → 架构师 → 开发者 → 测试工程师 → 代码审查员」五个角色流水线协作完成软件开发任务，并内置**反馈回环**——测试不通过或审查不通过时自动回到开发者修复，直至通过验收。前端通过 **SSE** 实时呈现每个智能体的思考与产出。

## 特性

- **五角色流水线**：每个角色有独立的系统提示词，前序产出自动注入后续角色上下文
- **条件回环**：判定「不通过」即回流开发者，带迭代上限（`MAX_ITERATIONS`）防止死循环
- **上下文预算控制**：按字符数截断历史（`MAX_CONTEXT_CHARS`），让 3B 级小模型在 8K 上下文内也能稳定运行
- **三档模型后端**：本地 Ollama / OpenAI 兼容接口 / 规则模板模拟，通过环境变量一键切换
- **零依赖前端**：原生 HTML/CSS/JS，无第三方框架、无 CDN
- **可视化**：SSE 实时推送角色状态与产出，右上角标注当前推理后端

## 快速开始

```bash
# 1. 安装依赖（建议使用虚拟环境）
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. 配置模型
copy .env.example .env         # 然后按需修改 .env

# 3. 启动
python -m multiagent.run --port 8081
```

访问 <http://127.0.0.1:8081>，输入开发任务（例如「实现一个待办事项管理器，支持增删改查」）后点击「启动多智能体协作」。

## 模型配置

`.env` 中通过 `LLM_PROVIDER` 选择推理后端：

| 取值 | 后端 | 说明 |
|---|---|---|
| `ollama` | 本地 Ollama | 默认 `qwen2.5:3b`，纯 CPU 可跑，无需联网、无需 API Key |
| `openai` | OpenAI 兼容接口 | 可对接 DeepSeek / 通义千问 / 智谱等，需配置 `OPENAI_API_KEY` |
| `mock` | 规则模板 | 无需模型，流程真实执行但文本为模板，用于演示与测试 |

未配置 `OPENAI_API_KEY` 时自动降级为 `mock`，服务不会启动失败；界面会明确标注「演示模式」，避免把模板输出误认为真实模型推理。

## 目录结构

```
multiagent/
├── core/
│   ├── llm.py          # LLM 抽象层：MockLLM / OllamaLLM / OpenAILLM
│   ├── graph.py        # LangGraph 状态图、条件路由、结论判定
│   └── config.py       # .env 加载与类型化读取
├── agents/
│   └── definitions.py  # 五个角色的提示词与元数据（含颜色、图标）
├── web/
│   └── server.py       # Flask：/api/run /api/status /api/events(SSE) /api/config
├── static/             # 前端页面（原生 HTML/CSS/JS）
├── docs/               # 项目说明与设计文档
└── run.py              # 启动入口
```

## 协作流程

```
产品经理 → 架构师 → 开发者 → 测试工程师 → 代码审查员
                      ↑            │              │
                      │  测试不通过  │   审查不通过  │
                      └────────────┴──────────────┘
```

- **产品经理**：分析需求、拆解子任务、定义验收标准
- **架构师**：技术选型、模块划分、接口设计
- **开发者**：实现代码、处理边界情况
- **测试工程师**：设计用例、给出测试结论
- **代码审查员**：审查质量与规范，输出「通过 / 不通过」

## 主要 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/roles` | 角色定义（名称、颜色、图标） |
| GET | `/api/config` | 当前推理后端与模型名 |
| POST | `/api/run` | 提交任务，后台启动协作 |
| GET | `/api/status` | 当前运行状态与协作历史 |
| GET | `/api/events` | SSE 事件流（首帧推送快照） |

## 实测性能

本机环境（AMD64 笔记本，纯 CPU，无 GPU）：

- 本地 `qwen2.5:3b`（Q4_K_M，约 7 tok/s）：完成一次五角色完整协作约 **340–390 秒**
- 模拟模式：约 **2 秒**

## 许可与声明

所用开源依赖均为宽松许可（MIT / BSD-3-Clause / Apache-2.0）。模型、数据、代码、API 与外部工具的详细来源与授权依据见 `multiagent/docs/` 下的《原创性与资源使用声明》。

**本仓库不含任何 API Key 或敏感信息**，密钥请通过 `.env` 在本地注入（`.env` 已被 `.gitignore` 排除）。
