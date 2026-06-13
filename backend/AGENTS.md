# AGENTS.md

## 项目背景

本项目是《软件工程》课程大作业“智能家居语音交互助手系统”的后端部分。

系统采用 Web 原型方式实现。前端使用 Vue 3 和浏览器 Web Speech API 完成真实语音输入，并将识别后的中文文本指令发送给后端。后端使用 FastAPI 接收文本指令，完成用户认证、中文指令解析、虚拟设备控制、设备状态持久化、操作日志、提醒、天气查询和场景联动。

本项目不接入真实智能家居硬件，使用数据库中的虚拟设备模拟真实家居设备。天气查询使用本地模拟数据，不调用外部天气 API。

## 技术栈

后端固定使用：

* Python 3.10+
* FastAPI
* SQLite
* SQLAlchemy
* Pydantic
* JWT
* pytest
* Uvicorn

不要使用：

* Spring Boot
* Django
* MySQL
* Redis
* Docker
* 外部大模型 API
* 外部天气 API
* 真实智能家居硬件
* 前端框架代码

除非后续明确要求，否则不要引入上述技术或服务。

## 核心约束

1. 后端必须是可运行的 FastAPI 项目，不能只写伪代码。
2. 设备状态必须持久化到 SQLite，不能只存储在内存中。
3. 真实语音识别由前端完成，后端只接收识别后的中文文本指令。
4. 天气查询使用本地模拟数据。
5. 所有核心接口必须出现在 Swagger 文档中。
6. 所有接口尽量统一返回 `success/code/message/data`。
7. 每次指令执行必须写入 `command_logs`。
8. 每次设备状态变化必须写入 `device_status_history`。
9. 密码必须哈希存储，不能明文存储。
10. 代码要模块化，便于写需求分析、软件设计、测试报告和项目管理文档。
11. 每个阶段完成后必须说明如何运行、如何测试、修改了哪些文件、是否有未完成项。

## 鉴权规则

除以下接口外，其余业务接口默认需要 JWT 鉴权：

* `GET /api/health`
* `POST /api/auth/register`
* `POST /api/auth/login`
* `GET /api/weather`

如果测试或前端对接需要临时放开接口，必须在 README 中明确说明原因。

## 推荐目录结构

请尽量采用如下后端目录结构：

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── session.py
│   │   └── init_db.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   └── utils/
├── tests/
├── data/
├── requirements.txt
├── README.md
├── run.py
└── AGENTS.md
```

## 必须实现的核心接口

统一使用 `/api` 前缀。

健康检查：

* `GET /api/health`

用户认证：

* `POST /api/auth/register`
* `POST /api/auth/login`
* `GET /api/auth/me`

房间与设备：

* `GET /api/rooms`
* `GET /api/devices`
* `GET /api/devices/{device_id}`
* `PATCH /api/devices/{device_id}/state`
* `GET /api/devices/{device_id}/history`
* `GET /api/dashboard`

中文指令：

* `POST /api/commands/parse`
* `POST /api/commands/execute`
* `GET /api/commands/logs`

提醒：

* `GET /api/reminders`
* `POST /api/reminders`
* `PATCH /api/reminders/{reminder_id}`
* `DELETE /api/reminders/{reminder_id}`

场景：

* `GET /api/scenes`
* `POST /api/scenes/{scene_id}/run`

天气：

* `GET /api/weather?city=北京`

如果天气接口未传入 `city`，默认返回本地模拟天气数据。

## 必须支持的中文指令

至少支持以下中文指令及常见变体：

* 打开客厅灯
* 开一下客厅灯
* 关闭卧室空调
* 关掉卧室空调
* 把卧室空调调到26度
* 空调设置为26度
* 将客厅灯亮度调到80
* 客厅灯调到80亮度
* 把电视音量调到30
* 查看客厅设备状态
* 查询卧室设备状态
* 开启睡眠模式
* 开启回家模式
* 开启离家模式
* 提醒我晚上八点吃药
* 提醒我20:00吃药
* 查询今天的天气
* 查询北京天气

## 统一返回格式

成功响应尽量使用：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {}
}
```

失败响应尽量使用：

```json
{
  "success": false,
  "code": "DEVICE_NOT_FOUND",
  "message": "未找到指定设备",
  "data": null
}
```

常见错误码：

* `OK`
* `INVALID_COMMAND`
* `ROOM_NOT_FOUND`
* `DEVICE_NOT_FOUND`
* `UNSUPPORTED_ACTION`
* `VALUE_OUT_OF_RANGE`
* `UNAUTHORIZED`
* `DATABASE_ERROR`

## 数据初始化要求

数据库初始化数据至少包括：

* 1 个默认家庭；
* 4 个房间：客厅、卧室、厨房、书房；
* 至少 10 个设备：

  * 客厅：灯、空调、电视、窗帘；
  * 卧室：灯、空调、窗帘；
  * 厨房：灯、排风扇；
  * 书房：灯、空调；
* 3 个场景：

  * 回家模式；
  * 睡眠模式；
  * 离家模式；
* 1 个默认测试用户。

## 数据库表要求

至少建立以下数据表：

1. `users`
2. `homes`
3. `rooms`
4. `devices`
5. `command_logs`
6. `device_status_history`
7. `reminders`
8. `scenes`
9. `scene_actions`

其中：

* `devices` 表必须保存设备类型、所属房间、开关状态、在线状态和 JSON 属性字段；
* `command_logs` 表必须记录原始指令、解析结果、执行结果、是否成功、错误信息、用户和时间；
* `device_status_history` 表必须记录设备状态变化前后的内容。

## 提醒模块限制

提醒模块只需要支持提醒事项的创建、查询、修改和删除。

不要实现真实后台定时推送、系统通知、消息队列、Celery、APScheduler 或长期后台任务。

## 测试要求

必须使用 pytest 编写测试，至少覆盖：

* 用户注册；
* 用户登录；
* 获取当前用户；
* 查询设备；
* 修改设备状态；
* 查询设备状态历史；
* 中文指令解析；
* 中文指令执行；
* 提醒功能；
* 场景执行；
* 天气查询；
* 异常指令处理。

异常测试至少覆盖：

* 空指令；
* 不存在的房间；
* 不存在的设备；
* 设备不支持的操作；
* 参数超出范围；
* 未登录访问受保护接口。

## README 要求

`README.md` 至少包含：

1. 项目简介；
2. 技术栈；
3. 目录结构；
4. 安装依赖命令；
5. 初始化数据库命令；
6. 启动后端命令；
7. 运行测试命令；
8. 默认账号密码；
9. 核心接口表；
10. 语音指令示例；
11. 前后端对接说明；
12. 数据库表说明；
13. 测试说明；
14. 已知限制；
15. 后续扩展方向。

## 每次任务完成后的汇报要求

每次完成开发任务后，请输出：

1. 新增和修改的文件列表；
2. 已实现功能；
3. 安装依赖命令；
4. 初始化数据库命令；
5. 启动后端命令；
6. 运行测试命令；
7. 默认账号密码；
8. 核心接口示例；
9. 当前是否有未完成项或需要人工确认的地方。
