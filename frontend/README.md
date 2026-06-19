# 智能家居语音交互助手系统前端

本目录是《软件工程》课程大作业的 Vue 3 前端。当前已完成统一视觉风格、Axios 请求封装、JWT 登录、Pinia 认证状态、路由守卫、基础布局、Dashboard、设备控制、设备别名管理、个性化语音设置、语音控制、操作日志详情、提醒管理和场景模式页面。

前端语音控制页提供三种输入路径：

```text
智能语音控制（MediaRecorder 上传音频）
浏览器识别（Web Speech API）
文本输入兜底
```

ASR 后纠错、方言归一、多指令拆分、指令解析、云端 ASR 调用和执行日志都由后端负责。前端不直连云端 ASR，也不保存 API Key。

## 技术栈

- Vue 3
- Vite
- JavaScript
- Element Plus
- Axios
- Vue Router
- Pinia
- MediaRecorder
- 浏览器 Web Speech API
- Speech Synthesis

未使用 TypeScript、React、外部语音 API、外部大模型 API 或真实硬件接口。

## 目录结构

```text
frontend/
├── src/
│   ├── api/
│   │   ├── command.js
│   │   ├── personalization.js
│   │   └── voice.js
│   ├── components/
│   │   ├── DeviceAliasDialog.vue
│   │   ├── LogDetailDrawer.vue
│   │   └── PersonalizationCard.vue
│   ├── config/
│   ├── router/
│   ├── stores/
│   ├── styles/
│   ├── utils/
│   │   └── normalizers.js
│   ├── views/
│   │   ├── LogsView.vue
│   │   └── VoiceControlView.vue
│   ├── App.vue
│   └── main.js
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

## 安装依赖

```bash
cd frontend
npm install
```

## 启动前端

```bash
cd frontend
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

## 后端启动

前端默认通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`。

```bash
cd backend
python -m app.db.init_db
python run.py
```

也可以使用：

```bash
cd backend
uvicorn app.main:app --reload
```

## 后端地址配置

默认 API baseURL：

```js
'/api'
```

配置文件：

```text
src/config/api.js
```

如果设置 `VITE_API_BASE_URL=http://127.0.0.1:8000/api` 让浏览器直连后端，需要后端启用 CORS。开发阶段建议保持默认 `/api` 代理。

## 默认账号

```text
用户名：testuser
密码：test123456
```

## 当前页面

- `/login`：登录页，已对接 `POST /api/auth/login`。
- `/dashboard`：Dashboard 首页，展示房间数量、设备总数、在线设备数、开启设备数、天气、快捷场景、设备类型分布、家庭平面总览和最近日志。
- `/devices`：设备管理页，展示房间筛选、设备卡片、在线/开关状态、属性调节、设备详情、设备历史抽屉和设备别名管理。
- `/voice`：语音控制页，展示 provider 状态，支持云端录音上传、浏览器识别、文本输入兜底、讯飞配置窗口和个性化设置弹窗。
- `/logs`：操作日志页，列表展示摘要，详情抽屉展示 ASR、方言容错、个性化命中、解析、批量执行信息和原始 JSON。
- `/reminders`：提醒管理页，支持列表、新建、编辑、状态修改和删除。
- `/scenes`：场景模式页，展示场景卡片并支持执行场景。

未登录访问业务页面会跳转 `/login`。登录成功后跳转 `/dashboard`。

## 已封装接口

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard`
- `GET /api/rooms`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `PATCH /api/devices/{device_id}/state`
- `GET /api/devices/{device_id}/history`
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
- `GET /api/weather`
- `GET /api/scenes`
- `POST /api/scenes/{scene_id}/run`

## 语音控制说明

`/voice` 页面主流程为：

```text
正在听取指令
→ 正在理解语音
→ 正在执行控制
→ 控制完成
```

输入路径：

1. 智能语音控制：使用 MediaRecorder 录音并上传到 `POST /api/voice/execute`。
2. 浏览器识别：使用 Web Speech API 得到文本后调用 `POST /api/commands/execute`。
3. 文本输入：直接调用 `POST /api/commands/execute`。

能力状态来自：

```text
GET /api/voice/providers
```

页面展示：

- 云端 ASR：可用 / 未配置 / 调用失败
- 浏览器识别：支持 / 不支持
- 文本输入：可用

云端 ASR 未配置时，页面提示：

```text
云端语音识别未配置，请使用浏览器识别或文本输入。
```

语音页执行后只展示简化摘要：

- 后端 message
- 识别意图
- 目标房间
- 目标设备
- 参数值
- 置信度
- 设备状态变化
- 低置信度提示

主页面不突出展示 transcript、normalized_text、dialect_matches、intent_scores 或 raw JSON；这些细节通过“查看日志详情”入口进入日志页查看。

如果后端返回批量执行结果，语音页只展示总体成功/失败条数和每条子指令的简短消息，不在主界面展示 raw JSON。

“配置讯飞”窗口只用于填写 AppID、APIKey、APISecret 三个必要配置，并通过后端接口保存到 `backend/data/asr_config.json`。保存后立即生效，不需要重启后端。前端不保存密钥、不直连讯飞，读取配置状态时只显示脱敏后的 AppID/APIKey 和 APISecret 是否已配置。

## 个性化交互说明

语音控制页的“个性化设置”按钮会打开独立弹窗，弹窗调用：

```text
GET /api/user/preferences
PATCH /api/user/preferences
GET /api/user/preference-suggestions
```

当前支持：

- 默认方言模式：自动、普通话、粤语、西南口音、东北口语。
- 默认输入方式：云端 ASR、浏览器识别、文本输入。

弹窗会展示“自动学习建议”：后端根据最近成功日志统计默认方言和默认输入方式，当某个候选至少出现 3 次且占比达到 60% 时，页面显示“应用”按钮。点击后仍通过 `PATCH /api/user/preferences` 保存，系统不会静默修改用户偏好。

设备页的设备别名管理调用：

```text
GET /api/user/device-aliases
POST /api/user/device-aliases
DELETE /api/user/device-aliases/{alias_id}
```

设备卡片会显示当前用户设置的别名。设置“客厅灯 -> 小灯”后，可在语音控制页执行“打开小灯”，后端会命中真实设备并在日志详情记录 `alias_match`。

语音控制页的“你的常用指令”调用：

```text
GET /api/user/frequent-commands
```

语音控制页会展示当前用户的动态常用指令列表；“普通指令”和“粤语/方言演示”这类静态推荐不在主页面展示。

## 演示指令

普通指令：

- 打开客厅灯
- 打开客厅灯和空调
- 打开卧室空调并调到26度
- 开启睡眠模式并提醒我晚上八点吃药
- 把卧室空调调到26度
- 开启睡眠模式
- 提醒我晚上八点吃药
- 查询北京天气

粤语/方言演示指令：

- 帮我打开客厅冷气
- 熄客厅灯
- 将电视机声量调到三十
- 提醒我今晚八点食药
- 开启瞓觉模式

这些指令可直接在语音控制页文本输入框中执行，便于课堂演示。

## 日志展示说明

日志列表展示摘要字段：

- 时间
- trace_id
- 原始指令
- 输入来源
- ASR provider
- 意图
- 目标房间
- 目标设备
- 置信度
- 成功/失败

日志详情抽屉分块展示：

- 链路概览
- 语音识别信息
- ASR 后纠错信息：corrected transcript 和 `asr_post_correction`
- 方言容错信息
- 指令解析信息，包括 Parser 置信度和 `confidence_breakdown` 分数拆解
- 批量执行信息
- 个性化命中信息：默认方言和设备别名
- 执行信息
- 原始 JSON

字段不存在时显示 `-`，避免出现 `undefined`、`null null` 或 `[object Object]`。

## 已确认的关键响应字段

`GET /api/voice/providers` 返回示例：

```json
{
  "success": true,
  "code": "OK",
  "message": "语音识别配置状态",
  "data": {
    "current_provider": "cloud",
    "cloud_configured": false,
    "available_providers": [],
    "browser_fallback_supported": true,
    "text_fallback_supported": true,
    "notes": "云端 ASR 未配置，可使用浏览器识别或文本输入兜底。"
  }
}
```

`POST /api/commands/execute` 请求体：

```json
{
  "command": "打开客厅灯"
}
```

`GET /api/commands/logs` 返回数组项会保留旧字段，并新增摘要字段和 `detail`：

```json
{
  "id": 1,
  "trace_id": "voice_20260615_120000_abcd12",
  "command_text": "帮我打开客厅冷气",
  "input_source": "cloud_asr",
  "asr_provider": "cloud",
  "intent": "turn_on",
  "room": "客厅",
  "device_type": "空调",
  "confidence": 0.92,
  "success": true,
  "message": "客厅空调已打开",
  "created_at": "...",
  "detail": {
    "asr": {},
    "normalization": {},
    "parse": {},
    "execution": {},
    "raw": {}
  }
}
```

## 前后端联调说明

1. 先启动后端 `python run.py`。
2. 再启动前端 `npm run dev`。
3. 浏览器访问 `http://127.0.0.1:5173`。
4. 使用默认账号登录。
5. 进入 Dashboard 后可通过左侧导航切换页面。

## 固定演示流程

1. 登录系统：使用 `testuser / test123456` 进入 Dashboard。
2. Dashboard：查看房间数量、设备总数、在线设备数、开启设备数、天气、快捷场景、设备类型分布、家庭平面总览和最近日志。
3. 语音控制页：确认 provider 状态。
4. 在个性化设置中保存：默认方言粤语。
5. 设备页：给“客厅灯”设置别名“小灯”，并查看设备卡片别名。
6. 回到语音控制页执行“打开小灯”。
7. 执行“查询北京天气”，确认天气查询可用。
8. 执行“将电视机声量调到三十”，确认粤语词“声量”被识别为音量。
9. 执行“打开客厅灯和空调”或“开启睡眠模式并提醒我晚上八点吃药”，查看批量结果。
10. 打开日志列表和日志详情，查看完整链路和个性化命中信息。

## 构建检查

```bash
cd frontend
npm run build
```

## 视觉风格

当前界面采用“智能家居控制中枢”方向：深色控制台背景、青蓝能量线、玻璃质感卡片和清晰的后台式导航。设计目标是适合课程演示、截图和录屏。

## 已知限制

- Web Speech API 依赖浏览器支持；不支持时可使用文本输入兜底。
- 云端 ASR 需要后端配置 API Key 和网络；未配置时使用浏览器识别或文本输入。
- 前端不接入云端 ASR 厂商 SDK。
- 常用指令推荐基于后端日志频次统计，不做复杂推荐算法。
- 设备别名仅对当前登录用户生效。
- 批量指令拆分在后端完成，前端只负责展示总体结果和子结果摘要。
- 方言容错由后端完成，前端只展示结果摘要和日志详情。
- 提醒模块只做前端 CRUD 展示，不做系统通知或后台定时推送。
- 后端当前未配置 CORS；开发环境通过 Vite `/api` 代理规避跨域。
