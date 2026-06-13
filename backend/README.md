# 智能家居语音交互助手系统后端

本项目是《软件工程》课程大作业“智能家居语音交互助手系统”的后端部分。当前已完成 FastAPI 项目骨架、SQLite 数据库模型、初始化数据、统一响应工具、健康检查、用户认证、房间与设备管理、中文指令解析与执行、提醒 CRUD、真实天气优先查询与本地备用天气、场景执行、指令日志和设备状态历史。

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
- `POST /api/commands/parse`：解析中文文本指令，需要登录，不执行设备控制。
- `POST /api/commands/execute`：解析并执行中文指令，需要登录。
- `GET /api/commands/logs`：查询当前用户指令执行日志。
- `GET /api/reminders`：查询提醒列表。
- `POST /api/reminders`：创建提醒。
- `PATCH /api/reminders/{reminder_id}`：修改提醒。
- `DELETE /api/reminders/{reminder_id}`：删除提醒。
- `GET /api/weather`：查询天气，优先使用 Open-Meteo，失败时自动回退本地备用数据，可不登录。
- `GET /api/scenes`：查询场景列表。
- `POST /api/scenes/{scene_id}/run`：执行场景。

## 前后端对接说明

前端使用 Vue 3 和浏览器 Web Speech API 进行真实语音识别，后端不接收音频文件，只接收前端识别后的中文文本。

推荐对接流程：

1. 前端调用 `POST /api/auth/login` 获取 `access_token`。
2. 前端在受保护接口请求头加入 `Authorization: Bearer <access_token>`。
3. 语音识别得到中文文本后，前端调用 `POST /api/commands/parse` 做解析预览，或调用 `POST /api/commands/execute` 直接执行。
4. 前端可通过 `GET /api/devices`、`GET /api/rooms`、`GET /api/dashboard` 刷新设备和统计状态。
5. 天气接口 `GET /api/weather` 可不登录调用；通过指令执行触发天气查询时仍需要登录。
6. 天气接口不改变调用路径，示例：`GET /api/weather?city=北京`。后端优先请求 Open-Meteo，3 秒超时；网络失败、超时或城市无法识别时返回本地备用数据。

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
    "intent": "set_temperature",
    "room": "卧室",
    "device_type": "air_conditioner",
    "value": 26,
    "scene": null,
    "reminder_time": null,
    "reminder_content": null,
    "city": null,
    "valid": true,
    "message": "解析成功"
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
- `command_logs`：指令日志表，预留记录原始指令、解析结果、执行结果和错误信息。
- `device_status_history`：设备状态历史表，预留记录状态变更前后内容。
- `reminders`：提醒表，预留提醒事项 CRUD。
- `scenes`：场景表，保存回家模式、睡眠模式、离家模式。
- `scene_actions`：场景动作表，保存场景关联设备及目标状态。

## 测试说明

测试位于 `tests/`，使用 pytest 和独立临时 SQLite 数据库，不污染 `data/app.db`。

当前测试覆盖：

- 用户注册、登录、获取当前用户。
- 未登录访问受保护接口。
- 房间、设备、dashboard、设备状态修改和设备状态历史。
- 中文指令解析、中文指令执行、异常指令。
- 提醒 CRUD、天气查询、场景列表和场景执行。
- 指令日志、设备状态历史、参数越界、不存在设备、不支持操作。
- 请求参数校验和未知路径的统一错误返回。

## 初始化数据

- 1 个默认家庭：默认家庭。
- 4 个房间：客厅、卧室、厨房、书房。
- 11 个设备：客厅灯、客厅空调、客厅电视、客厅窗帘、卧室灯、卧室空调、卧室窗帘、厨房灯、厨房排风扇、书房灯、书房空调。
- 3 个场景：回家模式、睡眠模式、离家模式。
- 1 个默认测试用户：`testuser`。

## 当前阶段限制

提醒模块只保存提醒事项，不做后台定时推送、系统通知、消息队列或长期后台任务。天气模块优先查询 Open-Meteo，失败时自动回退本地备用数据，确保无网络环境下仍可演示。

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
