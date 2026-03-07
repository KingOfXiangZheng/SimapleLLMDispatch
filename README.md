# ⚡ SimapleLLMDispatch

一个轻量级的 LLM API 智能调度代理，兼容 OpenAI API 格式。将多个 LLM 供应商统一为一个入口，自动处理负载均衡、配额管理、速率限制和故障切换。

## 功能特性

- **OpenAI 兼容** — 直接替换 `base_url` 即可使用，支持 `/v1/chat/completions` 和 `/v1/models`
- **多供应商管理** — 同时接入多个 LLM 供应商（OpenAI、Claude、DeepSeek、Gemini 等）
- **智能调度** — 支持加权随机（Weighted Random）和轮询（Round Robin）调度策略
- **多层级配额控制** — 
  - 供应商级别：RPD / RPM / TPM / 总请求 / 总 Token
  - 模型级别：每个模型可独立设置上述所有配额，并支持 **请求间隔时间（Interval）**
- **强大故障切换 (Failover)** — 
  - **自动重试**：供应商失败时自动尝试下一个可用供应商，支持多达 10 次递归重试。
  - **静默失败检测**：能够识别并拦截 `200 OK` 但内容包含 `abort` 或 `error` 的异常流，自动触发切换。
  - **空响应保护**：自动处理上游返回空响应体的情况。
- **健康检查与模型管理** — 
  - **自动冷却 (Cooldown)**：连续 3 次失败自动进入冷却期，支持 **自定义冷却时长**。
  - **逻辑禁用**：支持不删除配置的情况下保留模型信息并逻辑禁用（软删除）。
- **流式响应** — 完整支持 SSE 流式输出，自动预检首块数据以拦截早期错误。
- **可视化 Dashboard** — 玻璃质感暗色主题管理面板，实时查看健康状态、倒计时和配额。
- **调用审计** — 详尽的 `usage_logs`，支持按供应商、模型、错误状态过滤查询。
- **Docker 支持** — 提供 Dockerfile 和 docker-compose.yml，一键部署。

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 使用 docker compose 一键启动
docker compose up -d

# 或者手动构建运行
docker build -t simaple-llm-dispatch .
docker run -d -p 3100:3100 -v ./data:/app/data simaple-llm-dispatch
```

数据库文件持久化在宿主机 `./data/` 目录下，容器重建不会丢失数据。

### 方式二：直接运行

```bash
cd public
npm install 
npm run build

pip install -r requirements.txt
python app.py
```

服务默认运行在 `http://localhost:3100`，打开浏览器访问即可进入 Dashboard。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `3100` | 服务端口 |
| `DB_PATH` | `data/llm_dispatcher.db` | SQLite 数据库路径 |
| `UPSTREAM_TIMEOUT` | `60` | 上游请求超时（秒） |
| `DEBUG` | `0` | 设为 `1` 开启 Flask 调试模式（显示详细 Failover 日志） |

## 使用方式

启动后，将你的 LLM 客户端的 `base_url` 指向本服务即可：

```
http://localhost:3100/v1
```

### 示例：使用 Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3100/v1",
    api_key="any-key"  # API Key 由后端后台供应商配置决定
)

response = client.chat.completions.create(
    model="gpt-4", # 也可以使用你在后台配置的模型别名/分组
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

## 配额与健康管理

### 冷却机制
当一个模型连续失败 3 次时，系统会将其标记为“异常”。
- **冷却时间**：默认 300 秒（可在供应商模型配置中自定义）。
- **自动恢复**：冷却时间过后，下一次请求将尝试重新调用该供应商，成功则重置失败计数。

### 请求间隔
部分 API 供应商对并发有极严格限制（如每 5 秒只能请求一次）。通过设置模型级别的 **Interval**，Dispatcher 会自动延迟或跳过未到间隔时间的模型。

## 调度策略

- **加权随机（weighted_random）** — 按供应商权重随机分配，权重越高被选中概率越大。
- **轮询（round_robin）** — 按顺序依次分配。

## License

MIT
