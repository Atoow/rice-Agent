# 🌾 水稻种植智能 Agent（rice-Agent）

> 基于 LangGraph 多步推理 + Neo4j 知识图谱 + RAG 的水稻病虫害诊断系统

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-green)](https://langchain-ai.github.io/langgraph/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5+-4581C3?logo=neo4j)](https://neo4j.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 目录

- [系统架构](#-系统架构)
- [核心特性](#-核心特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [项目结构](#-项目结构)
- [API 接口](#-api-接口)
- [知识图谱](#-知识图谱)
- [Agent 推理流程](#-agent-推理流程)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (HTML + SSE)                     │
│              聊天界面 · 推理侧边栏 · 来源引用展示               │
└───────────────────────────┬─────────────────────────────────┘
                            │ POST /chat/stream (SSE)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 服务层 (routes/)                    │
│              SSE 流式推送 · interrupt/resume 追问             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               LangGraph 状态图 (agent/)                        │
│                                                               │
│   intent_route ──▶ collect_info ──▶ check_confidence         │
│        │                                 │                    │
│        │                    ┌────────────┼────────────┐      │
│        │                    ▼            ▼            ▼      │
│        │               verify_claim   clarify     (降级)     │
│        │                    │        (追问循环)              │
│        │                    ▼                                │
│        │              generate_plan                          │
│        │                                                    │
│        └──────────────────────▶ knowledge_answer              │
│                                                               │
│                    END (chitchat 直接回复)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Neo4j   │ │  Numpy   │ │  Ollama  │
        │ 知识图谱  │ │ 向量检索  │ │  LLM推理  │
        └──────────┘ └──────────┘ └──────────┘
```

---

## ✨ 核心特性

### 智能诊断
- **意图路由**：自动区分病虫害诊断、种植知识问答、日常闲聊
- **症状提取**：从自然语言描述中提取农业症状关键词
- **图谱推理**：在 Neo4j 知识图谱中查询症状-病害-防治关联关系
- **置信度评估**：LLM 评估诊断完整性，不足时主动追问（最多 3 轮）

### 追问机制
- 使用 LangGraph `interrupt()` + `Command(resume=...)` 实现真正的状态图暂停/恢复
- 同一 `session_id` 下多次请求会自动从断点恢复，无需前端维护状态

### 知识回答
- Numpy 向量检索引擎（余弦相似度），107+ 篇水稻标准文档
- 检索结果相关度排序，来源追溯

### 流式体验
- SSE（Server-Sent Events）实时推送推理过程
- 侧边栏展示每个节点的状态变化

---

## 🔧 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| **编排** | LangGraph 1.2 | 有状态多步推理状态图 |
| **LLM** | Ollama (qwen2.5) / DeepSeek | 本地优先，可切换云端 |
| **知识图谱** | Neo4j 5.x | 5 种病害、6 种实体、8 种关系 |
| **向量检索** | Numpy 自研 | 余弦相似度，磁盘持久化 |
| **Embedding** | dmeta-embedding-zh | 中文文本向量化 |
| **后端** | FastAPI + uvicorn | 异步高性能 |
| **前端** | 原生 HTML/JS + SSE | 零依赖 |

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Docker（仅 Neo4j 需要）
- Ollama（本地 LLM）

### 1. 克隆项目

```bash
git clone https://github.com/Atoow/rice-Agent.git
cd rice-Agent
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt --break-system-packages
```

### 3. 配置环境变量

```bash
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux
```

默认配置即可使用本地 Ollama + 本地 Neo4j，一般无需修改。

### 4. 拉取 LLM 和 Embedding 模型

```bash
ollama pull qwen2.5:3b                     # 推理模型
ollama pull shaw/dmeta-embedding-zh        # 中文 embedding
```

### 5. 启动 Neo4j

```bash
docker compose up -d neo4j
```

首次启动会自动下载 Neo4j 镜像（约 500MB），稍等片刻。

验证：浏览器打开 http://localhost:7474，用户名 `neo4j`，密码 `rice-agent-2026`。

### 6. 初始化知识图谱种子数据

```bash
python scripts/seed_kg.py
```

这会导入 5 种水稻病害的完整数据（症状、防治措施、品种抗性、环境触发、生育期关联）。

### 7. 导入文档到向量库

```bash
python scripts/ingest_docs.py
```

把 `data/documents/` 下的所有 PDF/TXT/MD 文档向量化存入 Numpy 向量库。

### 8. 启动后端

```bash
uvicorn backend.main:app --reload --port 8000
```

### 9. 打开前端

浏览器访问 **http://localhost:8000**，开始提问！

---

## ⚙ 配置说明

完整配置项在 `.env` 文件中：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `ollama` | LLM 后端：`ollama` / `deepseek` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama 服务地址 |
| `LLM_MODEL` | `qwen2.5:3b` | 推理模型名称 |
| `EMBED_MODEL` | `shaw/dmeta-embedding-zh` | Embedding 模型名称 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API Key（选填） |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j 连接地址 |
| `NEO4J_USER` | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | `rice-agent-2026` | Neo4j 密码 |
| `CONFIDENCE_THRESHOLD` | `0.7` | 诊断置信度阈值 |
| `MAX_CLARIFY_ROUNDS` | `3` | 最大追问轮数 |
| `RETRIEVAL_TOP_K` | `3` | 向量检索返回数量 |
| `MIN_RELEVANCE_SCORE` | `0.35` | 最低相关度阈值 |

---

## 📁 项目结构

```
rice-Agent/
├── backend/                      # 后端核心代码
│   ├── main.py                   # FastAPI 入口，依赖初始化
│   ├── config.py                 # 集中配置管理
│   │
│   ├── agent/                    # LangGraph 状态图
│   │   ├── state.py              # AgentState 定义 + 辅助函数
│   │   ├── graph.py              # 状态图编译 + 路由逻辑
│   │   ├── router.py             # 意图路由节点
│   │   └── nodes/
│   │       ├── collect.py        # 症状收集 + 图谱查询
│   │       ├── diagnose.py       # 置信度判断
│   │       ├── clarify.py        # 追问生成 + interrupt
│   │       ├── verify.py         # 图谱验证诊断链路
│   │       └── generate.py       # 方案生成 / 知识回答
│   │
│   ├── tools/                    # LangChain 工具
│   │   ├── graph_query.py        # Neo4j 只读查询
│   │   ├── vector_search.py      # 向量语义检索
│   │   ├── verify_claim.py       # 图谱三元组验证
│   │   └── calculator.py         # 农学计算器
│   │
│   ├── kg/                       # 知识图谱
│   │   ├── schema.py             # 图谱 Schema 定义
│   │   ├── builder.py            # 图构建器（MERGE）
│   │   └── seeder.py             # 种子数据导入
│   │
│   ├── rag/                      # 向量检索
│   │   ├── embedding.py          # Ollama Embedding 封装
│   │   ├── loader.py             # 文档加载（PDF/MD/TXT）
│   │   └── retriever.py          # Numpy 向量检索引擎
│   │
│   ├── llm/                      # LLM 抽象层
│   │   ├── provider.py           # Ollama / DeepSeek Provider
│   │   ├── factory.py            # Provider 工厂函数
│   │   └── prompts.py            # 全部 Prompt 模板
│   │
│   ├── db/                       # SQLite 对话持久化
│   │   └── models.py
│   │
│   ├── routes/                   # API 路由
│   │   ├── chat.py               # /chat/stream (SSE) + /chat
│   │   └── admin.py              # /admin/stats + /admin/upload
│   │
│   └── tests/                    # 测试
│       ├── test_agent_graph.py   # 状态图结构测试
│       └── test_tools.py         # 计算器单元测试
│
├── frontend/
│   ├── index.html                # 聊天界面
│   └── admin.html                # 管理后台
│
├── data/
│   ├── documents/                # 知识库文档
│   └── chroma_db/                # 向量数据（自动生成）
│
├── scripts/
│   ├── seed_kg.py                # 图谱初始化脚本
│   └── ingest_docs.py            # 文档摄入脚本
│
├── docker-compose.yml            # Neo4j 容器
├── Dockerfile                    # 应用容器化
├── requirements.txt
└── .env.example
```

---

## 📡 API 接口

### POST /chat/stream (SSE 流式)

```
POST /chat/stream
Content-Type: application/json

{
  "session_id": "abc123",
  "question": "水稻叶片上有褐色斑点是什么病？"
}
```

**SSE 事件类型：**

| type | content | 说明 |
|------|---------|------|
| `node_event` | `{node, status, data}` | 节点状态变化 |
| `clarify` | `string` | 追问问题文本 |
| `answer` | `string` | 最终回答 |
| `sources` | `[{source, relevance}]` | 来源引用 |
| `error` | `string` | 错误信息 |

**追问恢复：** 使用相同 `session_id` 再次调用，自动从 `interrupt()` 断点恢复。

### POST /chat (同步)

```json
// Request
{ "session_id": "abc123", "question": "稻瘟病怎么防治？" }

// Response
{
  "session_id": "abc123",
  "answer": "稻瘟病的防治措施包括...",
  "sources": [...],
  "reasoning_trace": [...]
}
```

### GET /api/health

```json
{ "status": "ok", "message": "水稻 Agent 运行中", "version": "2.0.0" }
```

### GET /admin/stats

返回向量库统计信息。

### POST /admin/upload

上传文档到知识库（PDF/MD/TXT）。

---

## 🧠 知识图谱

### 实体类型

| 标签 | 说明 | 示例 |
|------|------|------|
| `Disease` | 水稻病害 | 稻瘟病、纹枯病、稻飞虱 |
| `Symptom` | 症状表现 | 叶片褐色斑点、叶鞘腐烂 |
| `Control` | 防治措施 | 三环唑、井冈霉素、晒田 |
| `Variety` | 品种 | 宜香优2115、五优308 |
| `EnvCondition` | 环境条件 | 高温高湿、连续阴雨 |
| `GrowthStage` | 生育期 | 分蘖期、抽穗期、灌浆期 |

### 关系类型

| 关系 | 方向 | 说明 |
|------|------|------|
| `INDICATES` | Symptom → Disease | 症状指向病害（有权重） |
| `HAS_SYMPTOM` | Disease → Symptom | 病害有哪些症状 |
| `CONTROLLED_BY` | Disease → Control | 病害的防治方法 |
| `EFFECTIVE_AGAINST` | Control → Disease | 防治措施有效于 |
| `RESISTANT_TO` | Variety → Disease | 品种抗病性 |
| `SUSCEPTIBLE_TO` | Variety → Disease | 品种感病性 |
| `TRIGGERS` | EnvCondition → Disease | 环境触发条件 |
| `OCCURS_AT` | Disease → GrowthStage | 病害发生生育期 |

---

## 🔄 Agent 推理流程

### 诊断分支 (diagnose)

```
用户: "叶片有褐色斑点，边缘发黄"

  intent_route ──→ classify: diagnose
       │
       ▼
  collect_info ──→ extract: ["叶片褐色斑点", "叶缘发黄"]
       │           query Neo4j: MATCH (s:Symptom)... → 稻瘟病(0.8), 胡麻斑病(0.5)
       ▼
check_confidence ──→ assess: confidence=0.4, missing=["环境条件","品种"]
       │
       ├── confidence ≥ 0.7 → verify_claim → generate_plan → 输出方案
       │
       └── confidence < 0.7 ──→ clarify ──→ interrupt() 暂停
                                    │
                                    │  用户补充: "种的宜香优2115, 最近一直下雨"
                                    ▼
                              collect_info ←── Command(resume=...) 恢复
                                    │
                                    ▼
                              (循环直至确诊或 3 轮后降级输出)
```

### 知识问答分支 (knowledge)

```
用户: "如何选取水稻种子"

  intent_route ──→ classify: knowledge
       │
       ▼
knowledge_answer ──→ vector_search("如何选取水稻种子")
       │             检索到 3 篇相关文档片段
       ▼
   LLM 基于检索内容生成回答 → 输出答案 + 来源引用
```

### 闲聊分支 (chitchat)

```
用户: "你好"

  intent_route ──→ classify: chitchat
       │
       └── 生成欢迎消息 → END
```

---

## 💻 开发指南

### 运行测试

```bash
# 单元测试（无需外部依赖）
pytest backend/tests/test_tools.py -v

# 状态图结构测试
pytest backend/tests/test_agent_graph.py -v
```

### 添加新的 LLM Provider

1. 在 `backend/llm/provider.py` 中实现 `LLMProvider` 抽象类
2. 在 `backend/llm/factory.py` 中添加分支
3. 设置 `.env` 中 `LLM_PROVIDER` 为新名称

### 添加新的 Prompt 模板

在 `backend/llm/prompts.py` 中添加模板字符串，使用 `{variable}` 占位符，调用时用 `format_prompt(TEMPLATE, variable=value)` 安全格式化。

### 扩展知识图谱

编辑 `backend/kg/seeder.py` 中的种子数据，然后重新运行：

```bash
python scripts/seed_kg.py
```

---

## ❓ 常见问题

**Q: 启动时报 "No module named 'app'"？**

A: 确认当前目录在 `rice-Agent/` 下，启动命令是 `uvicorn backend.main:app --reload --port 8000`。

**Q: Ollama 返回空内容？**

A: 检查 `ollama pull qwen2.5:3b` 是否成功。如果是首次使用，模型下载可能需要几分钟。也可以换用 DeepSeek：设置 `.env` 中 `LLM_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY`。

**Q: Neo4j 连接失败？**

A: 确认 `docker compose up -d neo4j` 已启动，且密码为 `rice-agent-2026`。浏览器打开 http://localhost:7474 验证。

**Q: 向量检索返回空？**

A: 需要先运行 `python scripts/ingest_docs.py` 把 `data/documents/` 下的文档向量化入库。

**Q: 追问功能不生效？**

A: 前端需要保持同一个 `session_id`。每次创建新会话会重置状态图。

---

## 📄 License

MIT © 2026 Atoow

---

<p align="center">
  <b>🌾 让 AI 走进田间地头</b>
</p>
