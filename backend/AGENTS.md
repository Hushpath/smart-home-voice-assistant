# AGENTS.md

本文件适用于 `backend/`。详细架构、接口、配置和演示说明见 `backend/README.md`，这里只保留后端维护边界。

## 后端职责

后端使用 FastAPI，负责认证、设备、Dashboard、ASR Provider、方言/口音容错、指令解析与执行、操作日志、提醒、场景、天气和设备历史。

核心路径：

```text
云端 ASR 音频 / 浏览器识别文本 / 文本输入
→ ASRPostCorrector
→ DialectNormalizer
→ user_preferences / device_aliases context
→ MultiCommandParser
→ CommandParser
→ device_capabilities 校验
→ CommandExecutor
```

## 优先查看

- `backend/README.md`
- `app/routers/`
- `app/schemas/`
- `app/models/`
- `app/services/`
- `tests/`

代码和测试优先于文档；发现不一致时同步修正文档。

## 维护边界

- 保持 `/api/...` 路由和统一响应格式 `success/code/message/data` 稳定。
- 默认业务接口需要 JWT，公开接口只限健康检查、注册、登录和天气。
- 不随意修改数据库结构；日志详情优先复用已有 JSON 字段。
- 设备状态变化必须持久化，并写入 `device_status_history`。
- 指令成功或失败都应写入 `command_logs`，且一次执行不要重复写日志。
- 提醒模块只做 CRUD，不实现后台通知或长期定时任务。
- 天气请求必须有超时和本地兜底，测试不能依赖真实外网。
- 不引入大型转码依赖、外部大模型 API、真实硬件 SDK、消息队列或后台任务框架，除非用户明确要求。

## 语音与 ASR

- 前端不能直连云端 ASR。
- API Key、Secret、App ID 只能来自环境变量、`.env` 加载结果或后端本地配置文件 `backend/data/asr_config.json`。
- 没有明确厂商官方文档时，只保留 Provider 抽象、配置校验、HTTP 框架、错误处理和扩展点。
- 云端 ASR 未配置时返回 `ASR_PROVIDER_NOT_CONFIGURED` 和 fallback 建议，不在后端静默回退浏览器识别。
- `MockASRProvider` 只能用于 pytest、smoke test 或本地开发测试。
- 不引入 ffmpeg、pydub 等大型转码依赖。

## 指令与日志

- ASR 后纠错位于 `app/services/asr_post_corrector.py`，只做领域词表内的保守文本修正，并记录 `asr_post_correction`。
- 方言容错位于 `app/services/dialect_normalizer.py`，不直接决定业务执行。
- 方言词典替换必须最长匹配优先。
- `/api/commands/parse` 和 `/api/commands/execute` 请求体 `{ "command": "..." }` 保持兼容。
- 用户偏好和设备别名走 `app/services/personalization.py`，`/api/user/*` 必须 JWT 鉴权。
- 设备别名命中时按当前用户 alias 绑定真实 `device_id`，并记录 `alias_match`；不要为了别名重写 `CommandParser`。
- 默认方言应进入 `CommandExecutor` context，并记录到日志详情。
- 默认方言和默认输入方式自动学习只能基于当前用户成功日志给出建议，不要静默修改用户配置。
- 多指令解析和批量执行在后端完成，单条指令响应结构保持兼容。
- 设备参数能力以 `app/services/device_capabilities.py` 为准；数值越界或枚举值不支持时不得执行设备状态修改。
- 低置信度设备控制类指令不得强行执行。
- `CommandExecutor` 优先作为唯一日志写入入口，通过 context 记录 trace_id、ASR、normalization、parse 和 execution 信息。

## 常用命令

```bash
cd backend
pip install -r requirements.txt
python -m app.db.init_db
python run.py
```

测试：

```bash
cd backend
python -m pytest
python scripts/smoke_test.py
```

仅修改文档时不强制运行测试，但最终说明中要写明原因。
