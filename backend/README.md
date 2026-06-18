# 智能家居语音交互助手系统后端

本项目是《软件工程》课程大作业“智能家居语音交互助手系统”的后端部分。当前已完成 FastAPI 项目骨架、SQLite 数据库模型、初始化数据、统一响应工具、健康检查、用户认证、房间与设备管理、中文指令解析与执行、多指令批量执行、提醒 CRUD、真实天气优先查询与本地备用天气、场景执行、指令日志和设备状态历史。

## 技术栈

- Python 3.10+
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- pytest
- Uvicorn
- httpx

## 目录结构

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── data/
├── tests/
├── requirements.txt
├── README.md
└── run.py
```

## 安装依赖

推荐方式是创建本地虚拟环境：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 初始化数据库

```bash
cd backend
python -m app.db.init_db
```

数据库文件默认生成在：

```text
backend/data/app.db
```

## 启动后端

```bash
cd backend
python run.py
```

也可以直接使用：

```bash
uvicorn app.main:app --reload
```

## 验证接口

健康检查：

```text
GET http://127.0.0.1:8000/api/health
```

预期返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {
    "status": "ok",
    "service": "智能家居语音交互助手系统"
  }
}
```

Swagger 文档：

```text
http://127.0.0.1:8000/docs
```

## 鉴权说明

除 `GET /api/health`、`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/weather` 外，当前业务接口需要在请求头中携带 JWT：

```text
Authorization: Bearer <access_token>
```

登录获取 token：

```text
POST /api/auth/login
```

请求体示例：

```json
{
  "username": "testuser",
  "password": "test123456"
}
```

## 当前接口

- `GET /api/health`：健康检查。
- `POST /api/auth/register`：用户注册。
- `POST /api/auth/login`：用户登录并返回 JWT token。
- `GET /api/auth/me`：获取当前登录用户。
- `GET /api/rooms`：查询房间列表。
- `GET /api/devices`：查询设备列表，支持 `room_id` 筛选。
- `GET /api/devices/{device_id}`：查询设备详情。
- `PATCH /api/devices/{device_id}/state`：修改设备状态。
- `GET /api/devices/{device_id}/history`：查询设备状态变更历史。
- `GET /api/dashboard`：查询房间和设备统计数据。
- `POST /api/commands/parse`：解析中文文本指令，需要登录，不执行设备控制；批量指令返回 `is_batch`、`command_count` 和 `sub_commands`。
- `POST /api/commands/execute`：解析并执行中文指令，需要登录；批量指令逐条执行并返回 `success_count`、`failed_count` 和 `sub_results`。
- `GET /api/commands/logs`：查询当前用户指令执行日志。
- `GET /api/voice/providers`：查询后端云端 ASR 配置状态，需要登录。
- `GET /api/voice/asr-config`：查询后端本地 ASR 配置状态，需要登录，只返回脱敏信息。
- `POST /api/voice/asr-config`：保存讯飞 ASR 配置到后端本地文件，需要登录。
- `DELETE /api/voice/asr-config`：清除后端本地 ASR 配置，需要登录。
- `POST /api/voice/recognize`：上传音频并转写为中文文本，需要登录，不执行设备控制。
- `POST /api/voice/execute`：上传音频、转写、解析并执行语音指令，需要登录。
- `GET /api/reminders`：查询提醒列表。
- `POST /api/reminders`：创建提醒。
- `PATCH /api/reminders/{reminder_id}`：修改提醒。
- `DELETE /api/reminders/{reminder_id}`：删除提醒。
- `GET /api/weather`：查询天气，优先使用 Open-Meteo，失败时自动回退本地备用数据，可不登录。
- `GET /api/scenes`：查询场景列表。
- `POST /api/scenes/{scene_id}/run`：执行场景。

## 前后端对接说明

前端使用 Vue 3 和浏览器 Web Speech API 进行本地语音识别时，仍可调用已有中文指令接口提交识别后的文本。云端 ASR 音频识别统一通过后端 `/api/voice/*` 接口转发，前端不直接连接云端 ASR。

推荐对接流程：

1. 前端调用 `POST /api/auth/login` 获取 `access_token`。
2. 前端在受保护接口请求头加入 `Authorization: Bearer <access_token>`。
3. 浏览器语音识别得到中文文本后，前端调用 `POST /api/commands/parse` 做解析预览，或调用 `POST /api/commands/execute` 直接执行。
4. 前端可通过 `GET /api/devices`、`GET /api/rooms`、`GET /api/dashboard` 刷新设备和统计状态。
5. 天气接口 `GET /api/weather` 可不登录调用；通过指令执行触发天气查询时仍需要登录。
6. 天气接口不改变调用路径，示例：`GET /api/weather?city=北京`。后端优先请求 Open-Meteo，3 秒超时；网络失败、超时或城市无法识别时返回本地备用数据。

## 可插拔语音控制架构说明

当前后端新增了可插拔 ASR Provider 基础架构，目标是让云端音频识别、浏览器识别结果和文本输入共存，而不是让前端直接连接云端厂商。

处理链路：

```text
前端上传音频 -> 后端 ASR Provider -> transcript -> 方言/口音容错扩展点 -> CommandParser -> CommandExecutor -> command_logs
```

职责划分：

- 前端不直接调用云端 ASR，不在前端保存 API Key、Secret 或 App ID。
- 后端封装 `ASRProvider` 抽象，统一提供 `name`、`is_configured()` 和 `recognize(audio_bytes, filename, content_type, dialect, trace_id)`。
- 云端 ASR 只负责把音频转成文本，不负责设备控制、场景、提醒或天气。
- 后端继续负责方言容错、中文指令解析和指令执行；方言容错由 `DialectNormalizer` 统一处理并写入日志详情。
- 浏览器 Web Speech API 识别结果和手动文本输入仍作为兜底路径，继续使用已有 `/api/commands/parse`、`/api/commands/execute`。
- API Key、Secret、App ID 从环境变量读取，不写入源码。
- `MockASRProvider` 只用于 pytest、smoke test 或本地开发测试，不能作为前端用户可选择的识别方式。
- 每次 `/api/voice/recognize` 和 `/api/voice/execute` 都生成 `voice_YYYYMMDD_HHMMSS_random` 格式的 `trace_id`，用于串联识别、解析、执行和日志。

云端 ASR 环境变量：

```text
ASR_PROVIDER=xunfei
ASR_BASE_URL=wss://iat-api.xfyun.cn/v2/iat
ASR_API_KEY=your-xunfei-api-key
ASR_SECRET_KEY=your-xunfei-api-secret
ASR_APP_ID=your-xunfei-app-id
ASR_TIMEOUT_SECONDS=10
ASR_ENABLE_CLOUD=true
```

后端优先读取 `backend/data/asr_config.json`，该文件可由前端“配置讯飞”窗口通过 `/api/voice/asr-config` 写入；文件不存在时再读取进程环境变量。当前代码不会自动加载 `.env` 文件。如果希望使用 `.env` 文件，需要先在启动脚本或终端中把变量加载到环境中，或后续接入 `python-dotenv` 等配置加载方式。

当前已选择并适配讯飞语音听写；其他厂商仍只保留通用请求框架，必须按官方文档再实现签名、请求参数和响应解析。

音频接口支持的 content type：

- `audio/webm`
- `audio/wav`
- `audio/mpeg`

当云端 ASR 未配置时，`GET /api/voice/providers` 会返回 `cloud_configured=false`，并提示可使用浏览器识别或文本输入兜底。`POST /api/voice/recognize` 与 `POST /api/voice/execute` 会返回统一错误 `ASR_PROVIDER_NOT_CONFIGURED`。

### 云端 ASR 配置说明

前端不直接调用云端 ASR，原因是 API Key、Secret、App ID 等敏感配置不能暴露在浏览器中。前端只负责录音和上传音频，后端统一完成配置校验、云端请求、超时处理和错误映射。

后端运行环境变量示例：

```text
ASR_PROVIDER=xunfei
ASR_BASE_URL=wss://iat-api.xfyun.cn/v2/iat
ASR_API_KEY=your-xunfei-api-key
ASR_SECRET_KEY=your-xunfei-api-secret
ASR_APP_ID=your-xunfei-app-id
ASR_TIMEOUT_SECONDS=10
ASR_ENABLE_CLOUD=true
```

当前代码直接读取进程环境变量，不会自动加载 `.env` 文件。如果希望使用 `.env` 文件，需要先在启动脚本或终端中把变量加载到环境中，或后续接入 `python-dotenv` 等配置加载方式。

不要把这些密钥写进前端源码、后端源码或代码仓库。`backend/data/asr_config.json` 已在 `.gitignore` 中忽略；接口返回时只展示脱敏后的 AppID/APIKey 状态和 APISecret 是否配置。

### 讯飞语音听写

本项目已适配讯飞语音听写 WebAPI。配置 `ASR_PROVIDER=xunfei` 或 `ASR_PROVIDER=iflytek` 后，`CloudASRProvider` 会使用讯飞 WebSocket 鉴权、分帧上传和结果解析。`ASR_BASE_URL` 可省略，默认值是：

```text
wss://iat-api.xfyun.cn/v2/iat
```

环境变量对应关系：

- `ASR_APP_ID`：讯飞控制台 AppID。
- `ASR_API_KEY`：讯飞控制台 APIKey。
- `ASR_SECRET_KEY`：讯飞控制台 APISecret。
- `ASR_TIMEOUT_SECONDS`：WebSocket 连接和识别超时时间。

当前不做音频转码，不引入 ffmpeg、pydub 等大型依赖。讯飞路径只接受：

- `audio/wav`
- `audio/mpeg`

浏览器 `MediaRecorder` 常见默认格式是 `audio/webm`，讯飞语音听写不能直接识别该格式。当前前端会在讯飞模式下使用 Web Audio 采集语音并编码为 wav 上传；浏览器识别和文本输入仍作为兜底。

`ASR_PROVIDER=cloud` 仍保留通用 HTTP multipart 调用框架，用于后续接入其他厂商或自建 ASR 代理。

`GET /api/voice/providers` 返回示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "语音识别配置状态",
  "data": {
    "current_provider": "xunfei",
    "cloud_configured": false,
    "cloud_status": {
      "provider": "xunfei",
      "configured_provider": "xunfei",
      "base_url_configured": false,
      "credentials_configured": false,
      "app_id_configured": false,
      "secret_key_configured": false,
      "timeout_seconds": 10.0,
      "enable_cloud": false,
      "configured": false,
      "missing_fields": ["ASR_ENABLE_CLOUD=true", "ASR_APP_ID", "ASR_API_KEY", "ASR_SECRET_KEY"]
    },
    "available_providers": [],
    "browser_fallback_supported": true,
    "text_fallback_supported": true,
    "fallback": ["browser_speech", "text_input"],
    "notes": "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。"
  }
}
```

未配置时，语音执行接口返回：

```json
{
  "success": false,
  "code": "ASR_PROVIDER_NOT_CONFIGURED",
  "message": "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。",
  "data": {
    "trace_id": "voice_20260615_120000_abcd1234",
    "input_source": "cloud_asr",
    "asr_provider": "xunfei",
    "success": false,
    "error_code": "ASR_PROVIDER_NOT_CONFIGURED",
    "error_message": "云端语音识别服务未配置，请使用浏览器识别或文本输入兜底。",
    "latency_ms": 0,
    "fallback": ["browser_speech", "text_input"]
  }
}
```

常见错误码：

- `ASR_PROVIDER_NOT_CONFIGURED`：云端 ASR 未配置。
- `ASR_TIMEOUT`：云端 ASR 请求超时。
- `ASR_AUTH_FAILED`：云端认证失败，检查后端密钥配置。
- `ASR_EMPTY_TRANSCRIPT`：云端返回空文本。
- `ASR_REQUEST_FAILED`：云端请求失败或返回 HTTP 错误。
- `ASR_INVALID_RESPONSE`：云端响应不是预期 JSON 结构。
- `ASR_UNSUPPORTED_AUDIO_FORMAT`：音频格式不符合当前 provider 要求；讯飞路径只支持 `audio/wav`、`audio/mpeg`。

当前 `CloudASRProvider` 已包含讯飞 WebSocket 实现，并保留通用 HTTP 请求框架。后续接入其他厂商时，建议新增具体 provider 或继承 `CloudASRProvider`，只在厂商官方文档明确后实现：

- 请求路径和参数字段。
- 官方签名算法。
- 鉴权头或 token 获取方式。
- 响应字段映射到 `transcript`、`confidence`、`duration`。
- 厂商错误码到本项目统一错误码的映射。

`MockASRProvider` 只能通过测试或本地开发显式启用，不作为前端可选识别方式。

## 方言/口音容错设计说明

本项目不训练方言 ASR 模型，也不把方言理解下放到前端。方言/口音容错层位于 ASR 和 `CommandParser` 之间，统一处理云端 ASR transcript、浏览器识别文本和手动文本输入：

```text
ASR transcript / 浏览器识别文本 / 文本输入
-> DialectNormalizer
-> CommandParser
-> CommandExecutor
```

`DialectNormalizer` 只做文本归一和过程记录，不直接决定业务执行。输出会保留 `original_text`、`normalized_text`、`detected_dialect`、`dialect_matches`、`asr_corrections`、`removed_fillers`、`number_conversions` 和 `normalization_steps`。

后端内部支持 `auto`、`mandarin`、`cantonese`、`southwest`、`northeast`。默认 `auto`：命中 `冷气`、`声量`、`熄灯`、`睇下`、`食药`、`瞓觉`、`返屋企` 等识别为粤语；命中 `开哈`、`关哈` 识别为西南口音；命中 `开开`、`关上` 识别为东北/北方口语；其他情况按普通话处理。

粤语是当前重点支持方向：

- 设备词：`冷气/冷氣 -> 空调`，`电灯/電燈/灯光/燈光 -> 灯`，`电视机/電視機 -> 电视`。
- 动作词：`开灯/開燈 -> 打开灯`，`熄灯/熄燈/关灯/關燈 -> 关闭灯`，`较到/調到/调到/整到 -> 设置`。
- 房间词：`客廳/大厅/大廳 -> 客厅`，`房/睡房 -> 卧室`，`廚房 -> 厨房`，`書房 -> 书房`。
- 参数词：`声量/聲量/声音/聲音 -> 音量`，`光度 -> 亮度`，`度数/度數 -> 温度`。
- 提醒、天气和场景：`今日 -> 今天`，`听日/聽日 -> 明天`，`睇下/睇吓 -> 查询`，`食药/食藥 -> 吃药`，`返屋企模式 -> 回家模式`，`瞓觉模式/瞓覺模式 -> 睡眠模式`。

其他口音轻量支持：

- 西南口音：`开哈 -> 打开`，`关哈 -> 关闭`，`整到/整成 -> 设置`，`冷气 -> 空调`。
- 东北/北方口语：`开开 -> 打开`，`关上 -> 关闭`，`整到 -> 设置`，`整亮点 -> 设置亮度`。

ASR 常见错词纠正包括：`客厅等 -> 客厅灯`、`卧室等 -> 卧室灯`、`空条/空跳 -> 空调`、`电视及 -> 电视机`、`音凉 -> 音量`、`两度 -> 亮度`、`二十留 -> 二十六`。中文数字转换复用现有指令解析中的中文数字逻辑，例如 `三十 -> 30`、`八十 -> 80`、`二十六 -> 26`、`晚上八点 -> 20:00`。

置信度处理：ASR 错词纠正后仍继续解析，但会轻微降低 `confidence`，并把 `match_type` 标记为 `fuzzy`；多处模糊匹配会继续降低 `confidence`；低于 `0.6` 的设备控制、场景执行、提醒创建等会改变状态的指令不会执行；查询天气、查询状态等只读操作可以返回结果但提示置信度较低。当前不做低置信度二次确认机制。

当前限制：方言词典是规则式轻量词典，不覆盖所有真实方言表达；未训练或微调语音识别模型；未接入真实智能家居硬件；暂未把方言模式暴露到前端主界面，默认使用 `auto`。

## 操作日志与可解释链路说明

`command_logs` 是指令执行的统一审计入口。后端不为一次语音执行重复写多条日志，而是由 `CommandExecutor` 在一次执行中写入一条记录，并把 voice 层、方言容错层和解析层传入的上下文保存到已有 JSON 字段：

- `parsed_result`：保存指令解析结果、`parse_detail`、方言归一化详情和 context。
- `execution_result`：保存执行结果、执行状态、错误信息、执行耗时和 context。

`trace_id` 用于串联一次请求中的完整链路：

```text
trace_id
-> ASR 识别信息
-> DialectNormalizer 方言/口音容错
-> CommandParser 指令解析
-> CommandExecutor 执行结果
-> command_logs 日志详情
```

文本指令会自动生成 `cmd_YYYYMMDD_HHMMSS_random` 格式的 `trace_id`。语音接口继续使用 `voice_YYYYMMDD_HHMMSS_random` 格式，并在 `/api/voice/execute` 中传入 `CommandExecutor`，因此 ASR、归一化、解析和执行结果能在同一条日志中查看。

`GET /api/commands/logs` 同时保留旧字段和新增摘要字段。旧字段包括 `raw_command`、`parsed_result`、`execution_result`、`success`、`error_message`、`created_at`；新增摘要字段包括 `trace_id`、`command_text`、`input_source`、`asr_provider`、`intent`、`room`、`device_type`、`confidence`、`message` 和 `detail`。

`detail` 按链路分块：

- `asr`：输入来源、ASR provider、transcript、ASR 置信度、音频时长、ASR 耗时和 raw ASR 结果。
- `normalization`：检测到的方言、标准化文本、方言词典命中、ASR 错词纠正、中文数字转换、过滤口语词和步骤记录。
- `parse`：意图、房间、设备、参数、场景、提醒、天气、意图打分、解析置信度、关键词和匹配方式。
- `execution`：成功状态、code、message、设备前后状态、影响设备、错误信息和执行耗时。
- `batch`：批量指令的拆分策略、子指令列表、子执行结果、成功数和失败数。
- `raw`：原始 `parsed_result`、`execution_result` 和 context，便于调试和答辩展示。

这种结构让语音控制主页面保持简洁，日志列表展示摘要，日志详情展示完整链路。对测试和维护也更直接：一个失败用例可以通过同一个 `trace_id` 定位是 ASR、方言归一、解析还是执行阶段的问题。

统一成功响应：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {}
}
```

统一失败响应：

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "错误信息",
  "data": null
}
```

## 中文指令解析

当前支持的意图：

- `turn_on`：打开设备。
- `turn_off`：关闭设备。
- `set_temperature`：设置温度。
- `set_brightness`：设置亮度。
- `set_volume`：设置音量。
- `query_status`：查询设备状态。
- `run_scene`：执行场景。
- `create_reminder`：创建提醒。
- `query_weather`：查询天气。

请求示例：

```json
{
  "command": "把卧室空调调到26度"
}
```

响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "解析成功",
  "data": {
    "original_text": "把卧室空调调到二十六度",
    "normalized_text": "把卧室空调设置26度",
    "intent": "set_temperature",
    "room": "卧室",
    "device_type": "air_conditioner",
    "value": 26,
    "scene": null,
    "reminder_time": null,
    "reminder_content": null,
    "city": null,
    "confidence": 0.95,
    "matched_keywords": ["卧室", "空调", "二十六"],
    "match_type": "exact",
    "valid": true,
    "message": "识别为：设置温度为 26",
    "parse_detail": {
      "intent_scores": {
        "set_temperature": 7
      },
      "room_match": {},
      "device_match": {},
      "value_extract": {}
    }
  }
}
```

支持示例：

- 打开客厅灯
- 开一下客厅灯
- 关闭卧室空调
- 关掉卧室空调
- 把卧室空调调到26度
- 空调设置为26度
- 将客厅灯亮度调到80
- 客厅灯调到80亮度
- 把电视音量调到30
- 查看客厅设备状态
- 查询卧室设备状态
- 开启睡眠模式
- 开启回家模式
- 开启离家模式
- 提醒我晚上八点吃药
- 提醒我20:00吃药
- 查询今天的天气
- 查询北京天气

## 多指令解析与批量执行

`MultiCommandParser` 只负责拆分和补全子指令，不直接执行业务动作。它把一句话拆成现有 `CommandParser` 可以继续解析的文本，然后由 `CommandExecutor` 逐条执行。

支持的常见结构：

- 同一动作 + 同一房间 + 多设备：`打开客厅灯和空调` -> `打开客厅灯`、`打开客厅空调`。
- 同一动作 + 多房间 + 同一设备：`打开客厅和卧室的灯` -> `打开客厅灯`、`打开卧室灯`。
- 多个完整独立指令：`打开客厅灯并把卧室空调调到26度`。
- 上下文继承：`打开卧室空调并调到26度` -> `打开卧室空调`、`把卧室空调设置26度`。
- 短句继承和对象前置：`打开客厅灯并空调`、`客厅灯和空调都打开`。
- 混合业务指令：`开启睡眠模式并提醒我晚上八点吃药`、`查询北京天气并打开客厅灯`。

连接词包括 `和`、`并`、`并且`、`然后`、`接着`、`之后`、`随后`、`顺便`、`再`、`同时`、`以及`、`，`、`,`、`；`、`;`、`。`、`、`。批量中的状态改变类子指令如果缺少房间或设备，且无法从上下文继承，会标记 `AMBIGUOUS_SUB_COMMAND` 并跳过，避免误执行。批量执行不做整体回滚：已成功的子指令会保留，失败的子指令独立返回错误。部分成功时响应 `code=PARTIAL_SUCCESS`，`data` 中包含 `success_count`、`failed_count` 和 `sub_results`。

批量执行仍只写一条 `command_logs`，并在 `parsed_result.sub_commands`、`execution_result.sub_results` 和 `detail.batch` 中记录完整拆分和执行结果。每个实际改变设备状态的子指令仍会通过 `apply_device_state()` 写入 `device_status_history`。

## 鲁棒语音指令解析算法说明

算法目标是在浏览器 Web Speech API 得到中文文本后，后端对口语化表达、中文数字、设备别名和少量识别误差做可解释解析，不训练语音模型，不调用大模型 API。

处理流程：

```text
原始文本 -> 文本标准化 -> 同义词归一 -> 中文数字转换 -> 意图打分 -> 房间/设备匹配 -> 参数抽取与范围校验 -> 置信度计算 -> 结构化结果
```

文本标准化规则：

- 去除首尾空格、常见标点，统一全角/半角符号。
- 弱化口语词：请、帮我、麻烦、一下、可以、现在、给我。
- 同义词归一：开启/启动/开一下归一为打开，关闭/关掉/停止归一为关闭，调到/设为/设置为归一为设置。
- 设备别名归一：电灯/灯光归一为灯，电视机归一为电视，冷气归一为空调，声音归一为音量。
- 中文数字转阿拉伯数字：二十六转 26，八十转 80，晚上八点可提取为 20:00。

意图打分机制：

- `turn_on`：打开类动作词、设备词、房间词加分。
- `turn_off`：关闭类动作词、设备词、房间词加分。
- `set_temperature`：设置类动作词、空调词、温度/度、数字加分。
- `set_brightness`：亮度、灯、数字加分。
- `set_volume`：音量/声音、电视、数字加分。
- `query_status`：查询/查看与状态/设备组合加分。
- `run_scene`：场景名、模式/场景/打开类动作词加分。
- `create_reminder`：提醒、时间、提醒内容加分。
- `query_weather`：天气、查询/今天/城市加分。

匹配策略：

- 房间和设备优先精确匹配。
- 精确匹配失败时使用别名匹配，例如冷气匹配为空调、电视机匹配为电视。
- 别名匹配失败时使用 `difflib.SequenceMatcher` 做轻量模糊匹配，例如“打开客厅等”尽量匹配为客厅灯。
- 模糊匹配置信度过低时不会执行设备控制，会返回低置信度提示。

参数抽取与范围校验：

- 温度支持 `26度`、`二十六度`、`调到26`，范围 `16-30`。
- 亮度支持 `亮度80`、`亮度调到八十`，范围 `0-100`。
- 音量支持 `音量30`、`声音调到三十`，范围 `0-100`。
- 提醒时间支持 `晚上八点`、`20:00`、`明天早上八点`；当前提醒只保存时间，日期按创建当天处理。
- 参数越界返回 `VALUE_OUT_OF_RANGE`，不会执行设备状态修改。

置信度说明：

- `confidence` 范围为 `0-1`，由意图分数、房间匹配、设备匹配、参数明确性和模糊匹配惩罚综合计算。
- `0.80-1.00` 为高置信度，`0.60-0.79` 为中置信度，低于 `0.60` 视为低置信度。
- 低置信度设备控制类指令不会执行，并提示用户换一种说法或使用文本输入。

前端展示策略：

- 语音控制页展示简化摘要：意图、房间、设备、参数、置信度、执行前后状态。
- 操作日志页通过“详情”查看完整解析过程，包括 `intent_scores`、匹配关键词、房间/设备匹配、参数抽取和 raw JSON。

## 中文指令执行

执行接口会先调用规则式解析器，再执行业务动作。每次执行都会写入 `command_logs`；涉及设备状态变化时会写入 `device_status_history`。

请求示例：

```json
{
  "command": "打开客厅灯"
}
```

响应示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "指令执行成功",
  "data": {
    "parsed": {
      "intent": "turn_on",
      "room": "客厅",
      "device_type": "light",
      "value": null,
      "scene": null,
      "reminder_time": null,
      "reminder_content": null,
      "city": null,
      "valid": true,
      "message": "解析成功"
    },
    "result": {
      "before_state": {
        "is_on": false
      },
      "after_state": {
        "is_on": true
      }
    }
  }
}
```

执行支持：

- 打开、关闭设备。
- 设置空调温度，范围 `16-30`。
- 设置灯光亮度，范围 `0-100`。
- 设置电视音量，范围 `0-100`。
- 查询房间设备状态。
- 执行回家模式、睡眠模式、离家模式。
- 创建提醒。
- 查询天气，优先使用 Open-Meteo，失败时自动返回本地备用数据。

## 天气查询说明

`GET /api/weather?city=北京` 返回统一响应格式，`data` 中包含：

```json
{
  "city": "北京",
  "weather": "晴",
  "temperature": 28.4,
  "humidity": 35,
  "wind_speed": 8.2,
  "advice": "天气较适宜，可根据室内状态通风或调节设备。",
  "source": "open_meteo",
  "updated_at": "2026-06-13T10:00"
}
```

字段说明：

- `source=open_meteo`：数据来自 Open-Meteo。
- `source=mock`：真实天气请求失败、超时、网络不可用或城市无法识别时，返回本地备用数据。
- 当前内置经纬度映射支持：北京、上海、广州、深圳、杭州、南京、成都、重庆、西安、武汉。
- 同一城市真实天气结果会缓存 10 分钟，减少重复外部请求。
- pytest 默认 monkeypatch 外部天气请求，不依赖真实外网。

## 默认账号

```text
用户名：testuser
密码：test123456
```

密码在数据库中使用 PBKDF2-SHA256 哈希存储，不保存明文。

## 当前数据库表

- `users`：用户表，保存用户名、密码哈希、昵称、所属家庭和启用状态。
- `homes`：家庭表，保存默认家庭信息。
- `rooms`：房间表，保存客厅、卧室、厨房、书房。
- `devices`：设备表，保存设备类型、所属房间、开关状态、在线状态和 JSON 属性。
- `command_logs`：指令日志表，记录原始指令、解析结果、执行结果、成功状态和错误信息。
- `device_status_history`：设备状态历史表，记录状态变更前后内容、变更来源、用户和时间。
- `reminders`：提醒表，支持提醒事项创建、查询、修改和删除。
- `scenes`：场景表，保存回家模式、睡眠模式、离家模式。
- `scene_actions`：场景动作表，保存场景关联设备及目标状态。

## 测试说明

测试位于 `tests/`，使用 pytest 和独立临时 SQLite 数据库，不污染 `data/app.db`。

当前测试覆盖：

- 用户注册、登录、获取当前用户。
- 未登录访问受保护接口。
- 房间、设备、dashboard、设备状态修改和设备状态历史。
- 中文指令解析、中文指令执行、异常指令。
- 多指令解析、批量执行、部分成功、批量日志和多设备状态历史。
- 提醒 CRUD、天气查询、场景列表和场景执行。
- 指令日志、设备状态历史、参数越界、不存在设备、不支持操作。
- 请求参数校验和未知路径的统一错误返回。
- 云端 ASR 配置状态、未配置错误、超时、认证失败、空文本、非法响应和不支持音频格式。
- Mock ASR 测试路径、`/api/voice/providers`、`/api/voice/recognize`、`/api/voice/execute`。
- 方言/口音容错，包括粤语词典、西南/东北轻量口音、ASR 错词纠正和中文数字转换。
- 操作日志详情，包括 `trace_id`、ASR 信息、方言归一、解析结果、执行结果和避免重复日志。

## Smoke Test

后端提供一个只用于验收的 smoke test 脚本：

```bash
python scripts/smoke_test.py
```

该脚本使用临时 SQLite 数据库，不污染 `data/app.db`。它会在脚本进程内显式启用 `MockASRProvider`，验证：

- `GET /api/health`
- 默认账号登录
- `GET /api/dashboard`
- `GET /api/devices`
- `POST /api/commands/execute`
- `GET /api/voice/providers`
- `POST /api/voice/execute` 使用 Mock ASR
- `GET /api/commands/logs`
- `GET /api/devices/{device_id}/history`

`MockASRProvider` 只用于 pytest、smoke test 或本地开发验证，不作为前端主流程演示模式。

## 部署与演示说明

初始化数据库：

```bash
cd backend
python -m app.db.init_db
```

启动后端：

```bash
cd backend
python run.py
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

默认账号：

```text
用户名：testuser
密码：test123456
```

推荐演示流程：

1. 打开登录页，使用默认账号登录。
2. 查看 Dashboard，确认房间、设备和天气摘要正常。
3. 打开设备页，查看虚拟设备状态和设备历史入口。
4. 打开语音控制页，查看云端 ASR、浏览器识别、文本输入三种能力状态。
5. 云端 ASR 未配置时，展示“请使用浏览器识别或文本输入兜底”的提示。
6. 使用文本兜底依次执行：`打开客厅灯`、`把卧室空调调到26度`、`帮我打开客厅冷气`、`将电视机声量调到三十`、`开启瞓觉模式`、`提醒我今晚八点食药`。
7. 执行批量指令：`打开客厅灯和空调`、`打开卧室空调并调到26度`、`开启睡眠模式并提醒我晚上八点吃药`。
8. 打开操作日志页，查看日志列表摘要。
9. 打开一条日志详情，展示 ASR、方言容错、指令解析、批量子结果、执行结果和 raw JSON。
10. 回到设备页，查看设备状态历史。

推荐截图：

- 登录页。
- Dashboard。
- 语音控制页。
- 语音能力状态。
- 粤语指令执行结果。
- 批量指令执行结果。
- 操作日志列表。
- 操作日志详情。
- 设备页。
- 设备历史。
- `pytest` 通过结果。
- `npm run build` 通过结果。
- `python scripts/smoke_test.py` 通过结果。

## 初始化数据

- 1 个默认家庭：默认家庭。
- 4 个房间：客厅、卧室、厨房、书房。
- 11 个设备：客厅灯、客厅空调、客厅电视、客厅窗帘、卧室灯、卧室空调、卧室窗帘、厨房灯、厨房排风扇、书房灯、书房空调。
- 3 个场景：回家模式、睡眠模式、离家模式。
- 1 个默认测试用户：`testuser`。

## 已知限制

- 系统不训练自己的语音识别模型。
- 云端 ASR 需要 API Key、网络和厂商服务可用性。
- 未配置云端 ASR 时，前端应使用浏览器 Web Speech API 或文本输入兜底。
- 方言支持是有限场景下的指令容错，不是完整方言自然对话。
- 粤语是重点增强方向，但不是完整粤语对话系统。
- 多指令拆分是规则式能力，适合常见连接词、对象前置和上下文继承，并包含基础歧义保护；不覆盖任意复杂自然语言并列结构。
- 真实智能家居硬件未接入，当前使用虚拟设备模拟。
- 低置信度二次确认机制暂未实现。
- `MockASRProvider` 只用于测试和开发，不作为前端用户可选择的识别方式。
- 提醒模块只保存提醒事项，不做后台定时推送、系统通知、消息队列或长期后台任务。
- 天气模块优先查询 Open-Meteo，失败时自动回退本地备用数据，确保无网络环境下仍可演示。

## 后续扩展方向

- 增加更细的设备能力表，减少设备类型与属性规则的硬编码。
- 增加更多中文指令变体和歧义处理规则。
- 增加前端页面联调后的接口契约测试。
- 增加操作日志筛选、分页和导出能力。
- 增加更完整的用户家庭/成员管理。
- 可继续扩展更多城市、天气图标和前端天气趋势展示；当前版本不接入真实智能家居硬件。

## 软件工程文档支撑材料

文档同学可直接参考：[docs/software_engineering_support.md](docs/software_engineering_support.md)。

## 运行测试

```bash
python -m pytest
```
