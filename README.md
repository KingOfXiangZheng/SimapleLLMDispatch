# ⚡ SimapleLLMDispatch

一个轻量级的 LLM API 智能调度代理，兼容 OpenAI API 格式。将多个 LLM 供应商统一为一个入口，自动处理负载均衡、配额管理、速率限制和故障切换。

## 功能特性

- **OpenAI 兼容** — 直接替换 `base_url` 即可使用，支持 `/v1/chat/completions` 和 `/v1/models`
- **多供应商管理** — 同时接入多个 LLM 供应商（OpenAI、Claude、DeepSeek、Gemini 等）
- **智能调度** — 支持加权随机和轮询两种策略
- **多层级配额** — 供应商级别 + 模型级别，支持 RPD / RPM / TPM / 总请求数 / 总 Token 数
- **自动故障切换** — 供应商失败时自动重试下一个可用供应商
- **流式响应** — 完整支持 SSE 流式输出，自动提取 usage 信息
- **模型分组** — 将多个模型聚合为一个别名，统一对外暴露
- **可视化 Dashboard** — 暗色主题管理面板，实时查看配额使用情况
- **零外部依赖** — 仅需 Flask + SQLite，开箱即用
- **Docker 支持** — 提供 Dockerfile 和 docker-compose.yml，一键部署
- 模型间隔时间调用
- 模型冷却重试

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 使用 docker compose 一键启动
docker compose up -d

# 或者手动构建运行
docker build -t simaple-llm-dispatch .
docker run -d -p 3000:3000 -v ./data:/app/data simaple-llm-dispatch
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

服务默认运行在 `http://localhost:3000`，打开浏览器访问即可进入 Dashboard。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `3000` | 服务端口 |
| `DB_PATH` | `llm_dispatcher.db` | SQLite 数据库路径 |
| `UPSTREAM_TIMEOUT` | `30` | 上游请求超时（秒） |
| `DEBUG` | `0` | 设为 `1` 开启 Flask 调试模式 |

## 使用方式

启动后，将你的 LLM 客户端的 `base_url` 指向本服务即可：

```
http://localhost:3000/v1
```

### 示例：使用 curl 调用

```bash
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 示例：使用 Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/v1",
    api_key="any-key"  # API Key 由后端管理，此处随意填写
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## 项目结构

```
├── app.py              # Flask 应用入口
├── config.py           # 配置（端口、数据库路径、超时等）
├── database.py         # SQLite 初始化与自动迁移
├── models.py           # 数据访问层（Provider / Group / UsageLog DAO）
├── scheduler.py        # 调度引擎（策略模式、模型解析、配额检查）
├── rate_limiter.py     # 速率限制器（RPM 持久化 + TPM 内存滑动窗口）
├── routes/
│   ├── admin.py        # 管理 API（供应商 / 分组 / 日志 CRUD）
│   └── proxy.py        # OpenAI 兼容代理（chat completions / models）
├── public/
│   └── dashboard.html  # Vue 3 单文件 Dashboard
├── Dockerfile          # Docker 镜像构建
├── docker-compose.yml  # Docker Compose 编排
├── pic/                # 截图
└── requirements.txt    # Python 依赖
```

## 配额系统

支持两个层级的配额控制：

**供应商级别：**
- RPD（每日请求数）
- RPM（每分钟请求数）
- TPM（每分钟 Token 数）
- 总请求数上限
- 总 Token 上限

**模型级别（每个模型可独立设置）：**
- RPD / RPM / TPM / 总请求数 / 总 Token

设为 `0` 表示不限制。Dashboard 内置了常用供应商的速率预设（OpenAI Free/Tier1/Tier2、Claude、DeepSeek、Gemini 等），一键应用。

## 调度策略

- **加权随机（weighted_random）** — 按供应商权重随机分配，权重越高被选中概率越大
- **轮询（round_robin）** — 按顺序依次分配

通过模型分组功能，可以将不同供应商的模型聚合为一个别名。例如将多个供应商的 `gpt-4` 聚合为 `super-gpt`，客户端只需请求 `super-gpt` 即可自动调度。

## API 端点

### 代理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/chat/completions` | Chat Completions（兼容 OpenAI） |
| GET | `/v1/models` | 列出所有可用模型 |

### 管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/admin/providers` | 供应商列表 / 创建 |
| PUT/DELETE | `/admin/providers/<id>` | 更新 / 删除供应商 |
| POST | `/admin/providers/<id>/fetch-models` | 从供应商拉取模型列表 |
| GET | `/admin/providers/<id>/quota` | 查看供应商配额详情 |
| GET/POST | `/admin/groups` | 分组列表 / 创建 |
| PUT/DELETE | `/admin/groups/<id>` | 更新 / 删除分组 |
| GET | `/admin/logs` | 调用日志（支持分页） |

## License

MIT