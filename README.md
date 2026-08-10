# Shred

智能资料管理与分类工具 — 将零散的中文笔记、日记和备忘自动转化为结构化活动记录。

Shred helps you turn scattered Chinese notes, journals, and memos into structured activity records automatically using an LLM-compatible API.

## 前提条件 / Prerequisites

- Docker 和 Docker Compose
- 兼容 OpenAI API 的密钥（或使用任何兼容 OpenAI 协议的 API 服务）

## 快速开始 / Quick Start

```bash
cp .env.example .env
# 编辑 .env，填入 SHRED_OPENAI_API_KEY
docker compose up -d
```

打开浏览器访问 http://localhost:8000

## API 兼容提供商 / API-Compatible Providers

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SHRED_OPENAI_API_KEY` | API 密钥 | （必须填写） |
| `SHRED_API_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `SHRED_MODEL` | 模型名称 | 自动检测 |
| `SHRED_BIND_ADDRESS` | 监听地址 | `127.0.0.1` |
| `SHRED_PORT` | 监听端口 | `8000` |
| `SHRED_DATA_DIR` | 数据目录 | `./data` |

支持的兼容 API 包括 OpenAI、Azure OpenAI、Ollama、LM Studio、vLLM，以及任何提供 `/v1/chat/completions` 端点的服务。

## 数据备份 / Backup

所有数据存储在 `./data/shred.db`（SQLite 文件）中。备份时只需复制该文件：

```bash
cp data/shred.db data/shred-backup-$(date +%Y%m%d).db
```

## JSON 导出 / Export

在设置页面点击"导出数据"按钮，可下载完整的结构化 JSON 导出文件，包含所有分类、源消息和活动记录。

## 更新 / Updating

```bash
docker compose pull
docker compose up -d
```

## 安全说明 / Security Notes

- **默认仅监听本地回环地址 (127.0.0.1)**，确保数据不会被局域网内其他设备直接访问。
- 如需在局域网内使用，可设置 `SHRED_BIND_ADDRESS=0.0.0.0`，但**请注意安全风险**，建议配合反向代理和 HTTPS 使用。
- **PWA 功能需要 HTTPS**：安装为 PWA 需要在 HTTPS 环境下运行，否则 Service Worker 无法注册。
- **隐私提醒**：所有消息文本会发送至配置的 API 端点进行分类处理，请勿输入敏感个人信息。本工具不会将数据上传至除配置的 API 外的任何第三方服务。

## 运行测试 / Running Tests

```bash
# 后端测试
python -m pytest tests/backend -q

# 前端单元测试
cd frontend && npm run test:run && cd ..

# 类型检查
cd frontend && npx tsc --noEmit && cd ..

# E2E 测试
cd frontend && npx playwright test && cd ..
```

## 人工验收输入 / Manual Acceptance Tests

以下输入可用于验证系统功能：

1. **"饭吃了，快递取了，邮件回了。"** — 应生成 3 条活动记录
2. **"上午开会讨论了季度计划，下午写代码修复了登录 bug。"** — 应识别出"开会"和"写代码"两条记录，时间分别为上午和下午
3. **"昨天跟朋友约了这周末去看电影。"** — 应识别出两个不同时间的活动
4. **"买了牛奶、鸡蛋和面包。"** — 应生成一条购物类活动记录
5. **"去医院复查了血压"** — 应生成一条健康类活动记录

## v0.1 非目标 / Non-Goals

- 多用户支持
- OAuth / 第三方登录
- 移动端原生应用（仅 PWA）
- 数据同步 / 云存储
- 非中文语言处理
- 图片 / 语音输入
- 定时提醒 / 日历集成

## 故障排除 / Troubleshooting

### API 密钥为空 / Empty API Key

确认 `.env` 文件中 `SHRED_OPENAI_API_KEY` 已正确填写。可以通过设置页面测试连接状态。

### 模型返回无效 JSON / Model Returns Invalid JSON

部分较小模型可能不遵循 JSON 输出格式。建议使用支持 function calling 的模型，或在设置中更换更强的模型。

### 端口冲突 / Port Collision

如果 8000 端口被占用，可通过 `SHRED_PORT` 环境变量更改端口：

```bash
SHRED_PORT=3000 docker compose up -d
```

### Docker 卷权限问题 / Docker Volume Permissions

如果 `./data` 目录权限不正确，可手动创建并设置权限：

```bash
mkdir -p data
chmod 777 data
```

### 重置数据 / Resetting Data

```bash
docker compose down
rm -rf data
docker compose up -d
```

## 开源许可 / License

MIT License — 详见 [LICENSE](./LICENSE) 文件。
