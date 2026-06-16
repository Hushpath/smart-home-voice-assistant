# AGENTS.md

本文件给后续编码代理使用。详细项目说明、接口、演示流程和测试清单放在 `README.md`、`backend/README.md`、`frontend/README.md`，这里只保留工作边界和验证要求。

## 项目概况

本项目是《软件工程》课程大作业：智能家居语音交互助手系统。

技术栈：

- 后端：FastAPI、SQLite、SQLAlchemy、Pydantic、pytest。
- 前端：Vue 3、Vite、Element Plus、Axios、Pinia。

核心链路：

```text
前端录音 / 浏览器语音识别 / 文本输入
→ 后端 ASR Provider
→ DialectNormalizer
→ CommandParser
→ CommandExecutor
→ command_logs / device_status_history
```

## 工作原则

- 先读现有代码和测试，再改动。
- 保持修改小而直接，不做无关重构。
- 优先复用已有 router、schema、service、normalizer 和 JSON 字段。
- 不破坏已有接口，尤其是 `/api/commands/parse`、`/api/commands/execute`、`/api/commands/logs`。
- 不删除浏览器 Web Speech API 路径，不删除文本输入兜底。
- 前端不能直连云端 ASR，不能保存或硬编码 API Key。
- 未指定具体厂商和官方文档时，不要硬写云端 ASR 签名逻辑。
- `MockASRProvider` 只用于 pytest、smoke test 或本地开发测试。
- 不训练语音识别模型，不接入真实智能家居硬件。
- 不为日志功能大规模修改数据库结构。
- 一次指令执行不要重复写入多条 `command_logs`。

## 事实来源

优先查看：

- `README.md`
- `backend/README.md`
- `frontend/README.md`
- `backend/app/routers/`
- `backend/app/services/`
- `frontend/src/api/`
- `frontend/src/utils/normalizers.js`

如果文档与代码不一致，以当前代码和测试为准，并同步修正文档。

## 关键边界

- 语音控制主页面保持简洁，只展示执行摘要；ASR、方言归一、解析和执行细节放在日志详情。
- 方言/口音容错必须在后端完成，位于 ASR 和 `CommandParser` 之间。
- 云端 ASR 未配置时，后端返回清晰错误和 fallback 建议；浏览器识别由前端完成，后端不要静默回退。
- 低置信度二次确认机制暂不实现。
- 设备控制使用虚拟设备，状态变更必须写入设备历史。

## 验证要求

后端代码修改后运行：

```bash
cd backend
python -m pytest
```

前端代码修改后运行：

```bash
cd frontend
npm run build
```

涉及演示链路、登录、语音、日志或设备历史时，优先补充运行：

```bash
cd backend
python scripts/smoke_test.py
```

仅修改文档时不强制运行测试或构建，但最终说明中要写明原因。
