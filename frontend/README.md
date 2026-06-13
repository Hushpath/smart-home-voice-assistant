# 智能家居语音交互助手系统前端

本目录是《软件工程》课程大作业的 Vue 3 前端。当前已完成前端工程骨架、统一视觉风格、Axios 请求封装、JWT 登录、Pinia 认证状态、路由守卫、基础布局、Dashboard 首页、设备控制页、语音控制页、操作日志页、提醒管理页和场景模式页。

## 技术栈

- Vue 3
- Vite
- JavaScript
- Element Plus
- Axios
- Vue Router
- Pinia

未使用 TypeScript、React、外部语音 API、外部大模型 API 或真实硬件接口。

## 目录结构

```text
frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── config/
│   ├── router/
│   ├── stores/
│   ├── styles/
│   ├── utils/
│   ├── views/
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

如果设置 `VITE_API_BASE_URL=http://127.0.0.1:8000/api` 让浏览器直连后端，需要后端启用 CORS。当前检查到后端 `app/main.py` 未配置 CORS，因此开发阶段建议保持默认 `/api` 代理。

## 默认账号

```text
用户名：testuser
密码：test123456
```

## 已确认的后端登录契约

登录接口：

```text
POST /api/auth/login
```

请求体字段：

```json
{
  "username": "testuser",
  "password": "test123456"
}
```

后端统一响应成功时外层为：

```json
{
  "success": true,
  "code": "OK",
  "message": "登录成功",
  "data": {}
}
```

登录成功后 `data` 内字段：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "nickname": null,
    "home_id": 1,
    "is_active": true,
    "created_at": "..."
  }
}
```

请求受保护接口时前端自动添加：

```text
Authorization: Bearer <access_token>
```

## 当前页面

- `/login`：登录页，已对接 `POST /api/auth/login`。
- `/dashboard`：Dashboard 首页，已展示房间数量、设备总数、在线设备数、开启设备数、可切换城市天气、天气数据来源、最近指令日志和可执行快捷场景入口。
- `/devices`：设备管理页，已展示房间筛选、按房间分组的设备卡片、在线/开关状态、关键属性、设备详情、手动开关、常见属性调节和设备历史抽屉。
- `/voice`：语音控制页，已实现 Web Speech API 语音识别、文本兜底输入、`POST /api/commands/parse` 解析预览、`POST /api/commands/execute` 执行、后端 message 播报、设备状态刷新和最近日志刷新。
- `/logs`：操作日志页，已对接 `GET /api/commands/logs` 并用表格展示指令文本、意图、置信度、执行摘要、成功状态、错误信息和时间，支持查看解析详情、本地筛选、分页和 CSV 导出。
- `/reminders`：提醒管理页，已对接提醒列表、新建、编辑、状态修改和删除。
- `/scenes`：场景模式页，已展示场景卡片并支持执行场景。

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
- `GET /api/reminders`
- `POST /api/reminders`
- `PATCH /api/reminders/{reminder_id}`
- `DELETE /api/reminders/{reminder_id}`
- `GET /api/weather`
- `GET /api/scenes`
- `POST /api/scenes/{scene_id}/run`

## 已确认的日志、提醒、场景字段

`GET /api/commands/logs` 返回数组项字段：

```json
{
  "id": 1,
  "user_id": 1,
  "raw_command": "打开客厅灯",
  "parsed_result": {
    "original_text": "打开客厅灯",
    "normalized_text": "打开客厅灯",
    "intent": "turn_on",
    "room": "客厅",
    "device_type": "light",
    "confidence": 0.95,
    "matched_keywords": ["客厅", "灯"],
    "match_type": "exact",
    "parse_detail": {
      "intent_scores": {},
      "room_match": {},
      "device_match": {},
      "value_extract": {}
    }
  },
  "execution_result": {},
  "success": true,
  "error_message": null,
  "created_at": "..."
}
```

`GET /api/reminders` 返回数组项字段：

```json
{
  "id": 1,
  "user_id": 1,
  "title": "吃药",
  "remind_time": "2026-06-13T20:00:00",
  "is_done": false,
  "created_at": "...",
  "updated_at": "..."
}
```

`POST /api/reminders` 请求体：

```json
{
  "title": "吃药",
  "remind_time": "2026-06-13T20:00:00"
}
```

`PATCH /api/reminders/{reminder_id}` 请求体按需传递：

```json
{
  "title": "吃药",
  "remind_time": "2026-06-13T20:00:00",
  "is_done": true
}
```

`GET /api/scenes` 返回数组项字段：

```json
{
  "id": 1,
  "name": "睡眠模式",
  "description": "关闭客厅设备，调整卧室环境",
  "home_id": 1,
  "actions": [
    {
      "id": 1,
      "device_id": 1,
      "device_name": "客厅灯",
      "action": "set_state",
      "target_state": {
        "is_on": false
      },
      "sort_order": 1
    }
  ]
}
```

`POST /api/scenes/{scene_id}/run` 返回：

```json
{
  "scene": {
    "id": 1,
    "name": "睡眠模式"
  },
  "changes": []
}
```

`GET /api/weather?city=北京` 返回：

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

`source=open_meteo` 表示来自 Open-Meteo；`source=mock` 表示真实天气失败、超时、无网络或城市无法识别时使用本地备用数据。Dashboard 当前内置城市选项包括北京、上海、广州、深圳、杭州、南京、成都、重庆、西安、武汉和本地。

## 已确认的设备字段

`GET /api/devices` 返回数组项字段：

```json
{
  "id": 1,
  "name": "灯",
  "device_type": "light",
  "room_id": 1,
  "room_name": "客厅",
  "is_on": false,
  "is_online": true,
  "properties": {
    "brightness": 60,
    "color_temperature": "暖白"
  },
  "created_at": "...",
  "updated_at": "..."
}
```

`PATCH /api/devices/{device_id}/state` 请求体：

```json
{
  "is_on": true,
  "is_online": true,
  "properties": {}
}
```

前端手动开关只发送：

```json
{
  "is_on": true
}
```

前端属性调节通过同一接口发送：

```json
{
  "properties": {
    "temperature": 24,
    "mode": "除湿",
    "fan_speed": "中速"
  }
}
```

`GET /api/devices/{device_id}/history` 返回数组项字段：

```json
{
  "id": 1,
  "device_id": 1,
  "user_id": 1,
  "before_state": {},
  "after_state": {},
  "change_source": "manual",
  "created_at": "..."
}
```

## 语音控制说明

当前 `/voice` 页面已经使用浏览器 Web Speech API 识别中文文本，并调用：

```text
POST /api/commands/execute
```

请求体字段已经按后端 schema 确认为：

```json
{
  "command": "打开客厅灯"
}
```

执行成功后页面会刷新：

- `GET /api/devices`：更新当前设备状态快照。
- `GET /api/commands/logs`：更新最近执行记录。

页面也支持先调用：

```text
POST /api/commands/parse
```

用于展示解析预览。

语音控制页展示策略：

- 主区域只展示解析摘要：原始指令、标准化文本、意图、房间、设备、参数、置信度和执行前后状态。
- 完整算法细节默认折叠，通过“查看解析详情”展开。
- 低置信度指令会提示换一种说法，或使用文本输入兜底。

操作日志页展示策略：

- 表格展示指令文本、意图、置信度、执行摘要和成功/失败状态。
- 点击“详情”可查看完整解析过程，包括意图打分、关键词、房间匹配、设备匹配、参数抽取、执行结果和 raw JSON。

鲁棒解析演示指令：

- 打开客厅灯
- 开一下客厅电灯
- 帮我打开客厅灯
- 客厅灯开一下
- 把卧室空调调到二十六度
- 将客厅灯亮度调到八十
- 把电视机音量调到三十
- 打开客厅等
- 卧室冷气调到二十六度
- 开启睡眠模式
- 提醒我晚上八点吃药
- 查询今天的天气

## 前后端联调说明

1. 先启动后端 `python run.py`。
2. 再启动前端 `npm run dev`。
3. 浏览器访问 `http://127.0.0.1:5173`。
4. 使用默认账号登录。
5. 进入 Dashboard 后可通过左侧导航切换页面。

## 固定演示流程

1. 登录系统：使用 `testuser / test123456` 进入 Dashboard。
2. Dashboard：查看房间数量、设备总数、在线设备数、开启设备数、天气、快捷场景和最近日志。
3. 语音打开客厅灯：进入语音控制页，输入或说出“打开客厅灯”，查看执行结果和设备快照。
4. 语音调节卧室空调：输入或说出“把卧室空调调到26度”，确认执行结果中温度变更。
5. 执行睡眠模式：进入场景模式页，点击“睡眠模式”的执行按钮，查看批量设备变化和刷新后的设备状态。
6. 创建提醒：进入提醒管理页手动新建提醒，或在语音控制页执行“提醒我晚上八点吃药”。
7. 查看日志：进入操作日志页，刷新后查看指令文本、意图、执行摘要、成功状态和执行时间。

## 视觉风格

当前界面采用“智能家居控制中枢”方向：深色控制台背景、青蓝能量线、玻璃质感卡片和清晰的后台式导航。设计目标是适合课程演示、截图和录屏。

## 已知限制

- 设备控制页已实现基础开关、历史查看和常见属性调节；复杂设备能力仍由后端虚拟设备属性决定。
- Web Speech API 依赖浏览器支持；不支持时可使用文本输入兜底。
- 提醒模块只做前端 CRUD 展示，不做系统通知或后台定时推送。
- 后端当前未配置 CORS；开发环境通过 Vite `/api` 代理规避跨域。

## 后续扩展方向

- 增加更细的日志导出格式和导出字段配置。
- 增加设备属性编辑的校验提示和批量控制。
- 增加场景执行后的设备页跨页面自动刷新联动。
- 增加前端端到端测试脚本。
