# SimapleLLMDispatch (Node.js)

SimapleLLMDispatch 是一个专为 OpenAI 格式设计的大语言模型（LLM）调度中心。它能将多个上游 API 整合为一个统一且高可用的入口。

## ✨ 核心特性

根据你的需求，本项目实现了以下核心功能：

1.  **多供应商聚合 (Unified Gateway)**
    *   支持配置多个 `base_url`、`api_key`。
    *   对外提供统一的地址和 Token，用户无需理解后端负载，只需访问：`http://localhost:3000/v1`。

2.  **智能调度策略 (Smart Scheduling)**
    *   **轮询与加权 (Round Robin & Weighted Random)**: 根据预设权重或轮询机制分配请求。
    *   **限额意识 (Quota Aware)**: 动态监控每日限额，当某个 Provider 达到上限时，自动将其从候选名单中移除。
    *   **故障转移 (Failover)**: 若一个 Provider 请求失败，调度中心会尝试列表中的下一个可用节点，确保服务高可用。

3.  **自动预览与模型选择 (Model Discovery & Filtering)**
    *   **自动获得模型**: 支持一键从配置的 API 地址获取所有可用的模型列表。
    *   **精细化模型控制**: 用户可以手动勾选要使用的模型。调度中心仅在用户选中的模型范围内进行智能匹配和分发。

4.  **灵活的分批与分发 (Flexible Grouping & Batched Dispatching)**
    *   **模型别名与分组**: 支持将模型分批并设置别名（Model Groups）。例如，将 `gpt-4-turbo` 和 `claude-3-opus` 统一分发到 `super-llm` 这个别名下。
    *   **灵活调度**: 不同模型批次可以有不同的调度策略，满足复杂场景下的灵活需求。

## 🚀 快速开始

### 1. 环境准备
*   Node.js 18+ (推荐)
*   SQLite3

### 2. 安装依赖
```bash
npm install
```

### 3. 后端启动
```bash
node server.js
```
运行后，管理后台默认在 `http://localhost:3000/dashboard.html`（Vue 3 版正在开发中）。

## 🛠️ API & 管理

*   **统一入口**: `POST /v1/chat/completions`
*   **模型发现**: `POST /admin/providers/:id/fetch-models`
*   **配额管理**: 支持设置 `max_requests_per_day`。
*   **模型分组**: `POST /admin/groups` 配置别名逻辑。

## 🏗️ 架构说明
*   **后端**: 基于 Express 开发，使用 `better-sqlite3` 存储配置和日志。
*   **调度**: `scheduler.js` 负责核心的供应商选择逻辑。
*   **前端**: `public/dashboard.html` 提供基础界面，计划迁移至强交互的 Vue 3 界面。

## 📄 许可证
ISC License
