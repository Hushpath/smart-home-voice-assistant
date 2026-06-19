# 智能家居语音交互助手系统

本项目是《软件工程》课程大作业，使用 Web 应用形式实现智能家居语音交互助手。系统包含 FastAPI 后端和 Vue 3 前端，支持用户认证、设备控制、提醒、天气、场景、操作日志、设备历史，以及可插拔语音控制链路。

当前语音链路为：

```text
前端录音 / 浏览器语音识别 / 文本输入
→ 后端 ASR Provider
→ ASR 后纠错
→ 方言/口音容错层
→ 鲁棒指令解析
→ 设备能力表校验
→ 设备控制 / 场景 / 提醒 / 天气
→ 操作日志和设备历史
```

云端 ASR 是可选增强；未配置云端 ASR 时，前端会提示使用浏览器 Web Speech API 或文本输入兜底。

## 功能特性

- 用户注册、登录、JWT 鉴权和当前用户查询。
- Dashboard 展示房间、设备、天气、快捷场景、家庭平面总览和最近指令日志。
- 房间与设备查询，支持设备手动开关和状态历史查看。
- 三种指令输入路径：云端 ASR 音频上传、浏览器 Web Speech API、文本输入兜底。
- 可插拔 ASR Provider：当前提供云端 Provider 框架和测试用 Mock Provider。
- ASR 后纠错和方言/口音容错层：基于领域词表修正常见识别错词，重点增强粤语，轻量支持西南、东北/北方口语。
- 鲁棒中文指令解析与执行，支持设备控制、设备参数调节、状态查询、场景执行、提醒创建和天气查询。
- 多指令解析与批量执行，支持一句话中包含多个设备控制、场景、提醒或天气指令。
- 操作日志记录 trace_id、ASR、ASR 后纠错、方言归一、解析和执行全过程。
- 个性化语音交互：支持用户偏好、设备别名、默认方言自动学习建议和常用指令推荐。
- 提醒事项创建、查询、修改和删除。
- 场景模式执行，当前包含回家模式、睡眠模式和离家模式。
- 天气查询优先使用 Open-Meteo，失败时自动回退本地备用数据。
- 使用 SQLite 持久化设备状态、指令日志、提醒和场景数据。

## 技术栈

后端：

- Python 3.10+
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- Uvicorn
- pytest
- httpx

前端：

- Vue 3
- Vite
- JavaScript
- Element Plus
- Axios
- Vue Router
- Pinia

## 环境要求

- Python 3.10 或更高版本。
- Node.js 18 或更高版本。
- npm。
- Git。

## 项目结构

```text
software/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── routers/
│   │   │   ├── commands.py
│   │   │   └── voice.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── asr_providers/
│   │   │   ├── command_executor.py
│   │   │   ├── command_parser.py
│   │   │   ├── dialect_normalizer.py
│   │   │   ├── multi_command_parser.py
│   │   │   └── speech_recognition_service.py
│   │   ├── utils/
│   │   └── main.py
│   ├── data/
│   ├── docs/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   ├── run.py
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── utils/
│   │   └── views/
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
├── AGENTS.md
└── README.md
```

## 快速开始

### 1. 初始化并启动后端

推荐方式是创建本地虚拟环境：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.db.init_db
python run.py
```

后端默认地址：

```text
http://127.0.0.1:8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

### 2. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:5173
```

前端默认使用 Vite 代理，请求 `/api` 会转发到 `http://127.0.0.1:8000`。

## 默认账号

```text
用户名：testuser
密码：test123456
```

## 云端 ASR 配置

云端 ASR 只由后端调用，前端不会直接连接云端厂商，也不会保存 API Key。

可通过后端运行环境变量配置：

```env
ASR_PROVIDER=xunfei
ASR_BASE_URL=wss://iat-api.xfyun.cn/v2/iat
ASR_API_KEY=你的讯飞 APIKey
ASR_SECRET_KEY=你的讯飞 APISecret
ASR_APP_ID=你的讯飞 AppID
ASR_TIMEOUT_SECONDS=10
ASR_ENABLE_CLOUD=true
```

当前代码直接读取进程环境变量，不会自动加载 `.env` 文件。如果希望使用 `.env` 文件，需要先在启动脚本或终端中把变量加载到环境中，或后续接入 `python-dotenv` 等配置加载方式。

当前已适配讯飞语音听写 WebAPI：`ASR_PROVIDER=xunfei` 或 `ASR_PROVIDER=iflytek` 时，后端会使用讯飞 WebSocket 鉴权、分帧上传和结果解析。`ASR_BASE_URL` 可省略，默认使用 `wss://iat-api.xfyun.cn/v2/iat`。`ASR_API_KEY` 对应讯飞 APIKey，`ASR_SECRET_KEY` 对应 APISecret，`ASR_APP_ID` 对应 AppID。

项目仍保留通用 HTTP cloud 框架：`ASR_PROVIDER=cloud` 时会按通用 multipart HTTP 请求调用 `ASR_BASE_URL`，适合后续接入其他厂商或自建代理。

讯飞语音听写不支持浏览器默认 `audio/webm` 直接上传。当前后端只接受 `audio/wav` 或 `audio/mpeg` 走讯飞；前端在讯飞模式下会使用 Web Audio 采集语音并编码为 wav 上传。项目不会引入 ffmpeg、pydub 等大型转码依赖。

云端未配置时，`/api/voice/execute` 返回 `ASR_PROVIDER_NOT_CONFIGURED`，前端提示使用浏览器识别或文本输入兜底。

语音控制页提供“配置讯飞”窗口，只填写 AppID、APIKey、APISecret 三个必要配置，并调用后端保存到 `backend/data/asr_config.json`。配置保存后立即生效，不需要重启后端；前端不会保存密钥，也不会直连讯飞。读取配置状态时只返回脱敏信息。

常见错误码：

- `ASR_PROVIDER_NOT_CONFIGURED`
- `ASR_TIMEOUT`
- `ASR_AUTH_FAILED`
- `ASR_EMPTY_TRANSCRIPT`
- `ASR_REQUEST_FAILED`
- `ASR_INVALID_RESPONSE`
- `ASR_UNSUPPORTED_AUDIO_FORMAT`

`MockASRProvider` 只用于 pytest、smoke test 或本地开发测试，不作为前端可选识别方式。

## 常用命令

后端：

```bash
cd backend
python -m app.db.init_db
python run.py
python -m pytest
python scripts/smoke_test.py
```

前端：

```bash
cd frontend
npm run dev
npm run build
```

## 页面说明

- `/login`：登录页。
- `/dashboard`：系统概览。
- `/devices`：设备管理和设备历史。
- `/voice`：语音控制页，支持云端录音、浏览器识别和文本输入。
- `/logs`：指令执行日志，列表展示摘要，详情展示完整链路。
- `/reminders`：提醒管理。
- `/scenes`：场景模式。

## 接口概览

公开接口：

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/weather`

需要 JWT 鉴权的接口：

- `GET /api/auth/me`
- `GET /api/rooms`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `PATCH /api/devices/{device_id}/state`
- `GET /api/devices/{device_id}/history`
- `GET /api/dashboard`
- `POST /api/commands/parse`
- `POST /api/commands/execute`
- `GET /api/commands/logs`
- `GET /api/user/preferences`
- `PATCH /api/user/preferences`
- `GET /api/user/device-aliases`
- `POST /api/user/device-aliases`
- `DELETE /api/user/device-aliases/{alias_id}`
- `GET /api/user/frequent-commands`
- `GET /api/voice/providers`
- `POST /api/voice/recognize`
- `POST /api/voice/execute`
- `GET /api/reminders`
- `POST /api/reminders`
- `PATCH /api/reminders/{reminder_id}`
- `DELETE /api/reminders/{reminder_id}`
- `GET /api/scenes`
- `POST /api/scenes/{scene_id}/run`

统一响应格式：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {}
}
```

## 语音控制架构

系统保留三种输入路径：

1. 智能语音控制：前端使用 MediaRecorder 录音，上传到 `/api/voice/execute`，后端调用 ASR Provider 后执行指令。
2. 浏览器识别：前端使用 Web Speech API 得到文本，再调用 `/api/commands/execute`。
3. 文本输入：用户直接输入文本并调用 `/api/commands/execute`。

后端统一执行：

```text
ASR transcript / 浏览器识别文本 / 文本输入
→ ASRPostCorrector
→ DialectNormalizer
→ MultiCommandParser
→ CommandParser
→ device_capabilities
→ CommandExecutor
```

前端语音控制页只展示“听取指令、理解语音、执行控制、完成反馈”的主流程；transcript、normalized_text、dialect_matches、intent_scores 和原始 JSON 等调试信息放在日志详情中。

## 方言/口音容错

`ASRPostCorrector` 位于 ASR transcript / 浏览器识别文本 / 文本输入之后，使用固定高置信错词和当前用户的房间、设备、设备别名、场景、参数能力表生成领域词表，保守修正常见识别错词，例如 `冰香 -> 冰箱`、`空气进化器 -> 空气净化器`。纠错详情记录为 `asr_post_correction`。

`DialectNormalizer` 位于 ASR 后纠错和 `CommandParser` 之间，不直接决定业务执行，只输出标准化文本和归一化详情。

支持模式：

- `auto`
- `mandarin`
- `cantonese`
- `southwest`
- `northeast`

粤语重点增强示例：

- 冷气 / 冷氣 -> 空调
- 电灯 / 電燈 -> 灯
- 熄灯 / 熄燈 -> 关闭灯
- 声量 / 聲量 -> 音量
- 光度 -> 亮度
- 食药 / 食藥 -> 吃药
- 瞓觉模式 / 瞓覺模式 -> 睡眠模式
- 返屋企模式 -> 回家模式

其他口音轻量支持示例：

- 开哈 -> 打开
- 关哈 -> 关闭
- 开开 -> 打开
- 关上 -> 关闭
- 整亮点 -> 设置亮度

识别文本常见错词示例：

- 客厅等 -> 客厅灯
- 卧室等 -> 卧室灯
- 空条 / 空跳 -> 空调
- 音凉 -> 音量
- 两度 -> 亮度

## 指令示例

普通指令：

- 打开客厅灯
- 关闭卧室空调
- 把卧室空调调到26度
- 将客厅灯亮度调到80
- 把电视音量调到30
- 查看客厅设备状态
- 开启睡眠模式
- 开启回家模式
- 提醒我晚上八点吃药
- 查询北京天气

多指令示例：

- 打开客厅灯和空调
- 打开客厅灯、空调和电视
- 打开客厅和卧室的灯
- 打开客厅灯并把卧室空调调到26度
- 打开卧室空调并调到26度
- 开启睡眠模式并提醒我晚上八点吃药
- 将客厅灯亮度调到80并把电视音量调到30

粤语/方言演示指令：

- 帮我打开客厅冷气
- 熄客厅灯
- 熄客廳燈
- 将电视机声量调到三十
- 将客厅灯光亮度调到八十
- 提醒我今晚八点食药
- 开启瞓觉模式
- 开启返屋企模式
- 开哈客厅灯
- 客厅灯开开
- 打开客厅等
- 卧室空条调到二十六度

## 多指令解析与批量执行

`MultiCommandParser` 位于 `DialectNormalizer` 和 `CommandParser` 之间，用于把一句话拆成多条仍可由现有单条 parser 识别的子指令。已有单条指令不进入批量执行路径。

当前支持：

- 同一动作 + 同一房间 + 多设备：`打开客厅灯和空调` -> `打开客厅灯`、`打开客厅空调`。
- 同一动作 + 多房间 + 同一设备：`打开客厅和卧室的灯` -> `打开客厅灯`、`打开卧室灯`。
- 多个完整独立指令：`打开客厅灯并把卧室空调调到26度`。
- 上下文继承：`打开卧室空调并调到26度` 中第二条会继承“卧室空调”。
- 短句继承和对象前置：`打开客厅灯并空调`、`客厅灯和空调都打开`。
- 混合业务指令：场景、提醒、天气和设备控制可在同一句中组合。

`/api/commands/parse` 识别批量指令时返回 `is_batch=true`、`command_count` 和 `sub_commands`。`/api/commands/execute` 批量执行时逐条执行，返回 `success_count`、`failed_count` 和 `sub_results`；部分成功返回 `PARTIAL_SUCCESS`，不会回滚已经成功的子指令。批量中的状态改变类子指令如果缺少房间或设备，且无法从上下文继承，会标记 `AMBIGUOUS_SUB_COMMAND` 并跳过，避免误执行。语音执行路径 `/api/voice/execute` 复用同一批量执行能力。

## 操作日志与 trace_id

每次指令执行都会尽量生成唯一 `trace_id`，语音链路格式为：

```text
voice_YYYYMMDD_HHMMSS_random
```

日志详情记录：

- 输入来源：`cloud_asr`、`browser_speech`、`text_input`
- ASR 信息：provider、transcript、corrected_transcript、latency、raw_result、错误码和 `asr_post_correction`
- 方言归一：detected_dialect、normalized_text、dialect_matches、识别文本纠错、number_conversions、removed_fillers
- 指令解析：intent、room、device_type、value、scene、reminder、city、intent_scores、matched_keywords、match_type
- 执行结果：success、code、message、device_before、device_after、affected_devices、execution_latency_ms
- 批量链路：is_batch、command_count、sub_commands、sub_results、success_count、failed_count

`CommandExecutor` 是主要日志写入入口，避免一次执行重复写入多条 `command_logs`。

## 数据库说明

后端使用 SQLite，数据库文件生成位置：

```text
backend/data/app.db
```

主要数据表：

- `users`
- `homes`
- `rooms`
- `devices`
- `device_status_history`
- `command_logs`
- `user_preferences`
- `device_aliases`
- `reminders`
- `scenes`
- `scene_actions`

初始化数据包括 1 个默认家庭、4 个房间、20 个设备、3 个场景和 1 个默认测试用户。

## 天气功能

天气接口：

```text
GET /api/weather?city=北京
```

天气数据优先使用 Open-Meteo。外部请求失败、超时或城市无法识别时，后端会返回本地备用数据，并在返回字段中标记 `source: "mock"`。

## 测试与验收

运行后端测试：

```bash
cd backend
python -m pytest
```

运行后端 smoke test：

```bash
cd backend
python scripts/smoke_test.py
```

运行前端构建检查：

```bash
cd frontend
npm run build
```

推荐演示流程：

1. 初始化数据库并启动后端。
2. 启动前端并使用默认账号登录。
3. 进入语音控制页，确认 `/api/voice/providers` 状态。
4. 在个性化设置中保存：默认方言粤语。
5. 进入设备页。
6. 给“客厅灯”设置别名“小灯”。
7. 回到语音控制页。
8. 执行“打开小灯”，确认客厅灯被打开。
9. 执行“查询北京天气”，确认天气查询可用。
10. 执行“将电视机声量调到三十”，确认粤语词“声量”被识别为音量。
11. 打开操作日志页。
12. 查看日志详情，确认能看到 `preference_used` 和 `alias_match`。
13. 回到设备页，查看设备历史。

推荐截图：

- 登录页
- Dashboard
- 语音控制页
- 个性化设置
- 语音能力状态
- 设备别名管理
- 粤语指令执行结果
- 日志列表
- 日志详情
- 设备页
- 设备历史
- pytest 通过
- npm run build 通过
- smoke test 通过

## 已知限制

- 系统不训练自己的语音识别模型。
- 云端 ASR 需要 API Key 和网络；当前已适配讯飞语音听写，其他厂商仍需按官方文档扩展。
- 未配置云端 ASR 时，应使用浏览器识别或文本输入兜底。
- ASR 后纠错只在项目领域词表内保守修正，不做通用中文纠错。
- 方言支持是有限场景下的指令容错，不是完整方言自然对话。
- 多指令拆分是规则式能力，适合常见连接词、对象前置和共享上下文，并包含基础歧义保护；不覆盖任意复杂自然语言并列结构。
- 粤语是重点增强，但不是完整粤语对话系统。
- 系统使用 SQLite 中的虚拟设备，不接入真实智能家居硬件。
- 低置信度二次确认机制暂未实现。
- `MockASRProvider` 只用于测试和本地开发。
- 提醒模块只支持数据管理，不包含后台通知或定时推送。
- 天气查询依赖外网时可能失败，但会自动回退本地备用数据，保证演示稳定。

## 相关文档

- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 软件工程文档支撑材料：[backend/docs/software_engineering_support.md](backend/docs/software_engineering_support.md)
