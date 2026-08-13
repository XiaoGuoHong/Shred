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

打开浏览器访问 http://localhost:9400

## API 兼容提供商 / API-Compatible Providers

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SHRED_OPENAI_API_KEY` | API 密钥 | （必须填写） |
| `SHRED_API_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `SHRED_MODEL` | 模型名称 | 自动检测 |
| `SHRED_BIND_ADDRESS` | 监听地址 | `127.0.0.1` |
| `SHRED_PORT` | 监听端口 | `9400` |
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
# 后端测试（含覆盖率门槛：85%，零警告）
python -m pytest tests/backend -q

# 前端单元测试（覆盖率门槛见 vite.config.ts）
cd frontend && npm run test:run && cd ..

# 前端覆盖率报告
cd frontend && npm run test:coverage && cd ..

# 类型检查
cd frontend && npx tsc --noEmit && cd ..

# E2E 测试（3 条走浏览器 mock + 1 条走真实后端 + 假分类器）
cd frontend && npx playwright test && cd ..
```

E2E 的最后一条用例启动真实 FastAPI + SQLite 管线（`SHRED_E2E_FAKE_CLASSIFIER=1` 注入确定性假模型，数据写入独立的 `data/e2e-test.db`），验证"后端在真实进程里能否跑起来"。

## 人工验收输入 / Manual Acceptance Tests

以下输入可用于验证系统功能。**分类质量（相对时间解析、分类树生成、偏好记忆）已用真实模型跑通验收（deepseek-v4-flash，2026-08-13，11/11 事件）；更换模型后建议重跑。**

配置好 `SHRED_OPENAI_API_KEY` 后，逐条提交下面 5 条输入，共应产出 **11 条活动记录**：

1. **"龙珠改看完了"** — 1 条
2. **"昨天下午做了一部分 CCAF-R 的测试"** — 1 条（时间解析为昨天下午）
3. **"上午做了面试复盘，把简历改了，还约了下周一的面试。"** — 3 条（"约面试"应记录为已完成动作，不生成未来任务）
4. **"饭吃了，快递取了，邮件回了。"** — 3 条
5. **"拖地、浇花、关窗，都弄了。"** — 3 条

验收要点：事件数合计 11、源文本完整保留、相对时间解析正确、相关记录复用稳定分类、分类质量合理。手动验证结果与自动化测试分开记录，未配置 key 时此项不视为通过。

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

如果 9400 端口被占用，可通过 `SHRED_PORT` 环境变量更改端口：

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
