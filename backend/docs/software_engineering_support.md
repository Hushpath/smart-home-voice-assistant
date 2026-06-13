# 软件工程文档支撑材料

本文档用于支撑《软件工程》课程大作业的需求分析、软件设计、系统测试和项目管理文档编写。

## 后端模块划分

- `app/main.py`：FastAPI 应用入口，注册路由和全局异常处理。
- `app/core/`：配置、密码哈希、JWT 生成与校验、鉴权依赖。
- `app/db/`：SQLAlchemy 数据库连接、`Base`、数据库初始化脚本。
- `app/models/`：数据库 ORM 模型。
- `app/schemas/`：请求体 Pydantic 模型。
- `app/routers/`：HTTP API 路由，包括认证、设备、命令、提醒、天气、场景。
- `app/services/`：业务逻辑，包括指令解析、指令执行、设备状态变更、真实天气查询和本地备用天气。
- `app/utils/`：统一响应格式工具。
- `tests/`：pytest 自动化测试。

## 数据库表清单

- `users`：用户账号、密码哈希、昵称、所属家庭和启用状态。
- `homes`：家庭信息。
- `rooms`：房间信息，当前初始化客厅、卧室、厨房、书房。
- `devices`：虚拟设备，保存设备类型、房间、开关状态、在线状态和 JSON 属性。
- `command_logs`：中文指令执行日志，记录原始指令、解析结果、执行结果、成功标记和错误信息。
- `device_status_history`：设备状态变更历史，记录变更前后状态、用户和来源。
- `reminders`：提醒事项，支持创建、查询、修改和删除。
- `scenes`：场景信息，当前初始化回家模式、睡眠模式、离家模式。
- `scene_actions`：场景动作，记录场景对应的设备目标状态。

## 核心 API 清单

- 健康检查：`GET /api/health`
- 认证：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`
- 房间设备：`GET /api/rooms`、`GET /api/devices`、`GET /api/devices/{device_id}`、`PATCH /api/devices/{device_id}/state`、`GET /api/devices/{device_id}/history`、`GET /api/dashboard`
- 中文指令：`POST /api/commands/parse`、`POST /api/commands/execute`、`GET /api/commands/logs`
- 提醒：`GET /api/reminders`、`POST /api/reminders`、`PATCH /api/reminders/{reminder_id}`、`DELETE /api/reminders/{reminder_id}`
- 天气：`GET /api/weather`
- 场景：`GET /api/scenes`、`POST /api/scenes/{scene_id}/run`

## 指令解析流程

1. 前端通过 Web Speech API 将语音转换成中文文本。
2. 后端 `POST /api/commands/parse` 接收中文文本。
3. `CommandParser` 对文本做标准化：去空格、去标点、全角半角统一、口语词弱化。
4. 对动作词、设备词和参数词做同义词归一，例如“开一下”归一为“打开”，“冷气”归一为“空调”，“声音”归一为“音量”。
5. 将中文数字转换为阿拉伯数字，并抽取温度、亮度、音量和提醒时间。
6. 基于动作词、设备词、房间词、数值词、单位词和场景/天气/提醒关键词计算各 intent 分数。
7. 房间和设备先做精确匹配，再做别名匹配，最后用 `difflib.SequenceMatcher` 做轻量模糊匹配。
8. 解析成功返回 `intent`、`room`、`device_type`、`value`、`scene`、`reminder_time`、`reminder_content`、`city`、`confidence`、`matched_keywords`、`match_type` 和 `parse_detail` 等结构化字段。
9. 低置信度指令返回明确提示，不执行设备控制。
6. 解析失败返回统一错误码 `INVALID_COMMAND`。

## 指令执行流程

1. 前端调用 `POST /api/commands/execute` 并携带 JWT。
2. 后端先调用 `CommandParser` 得到结构化解析结果。
3. `CommandExecutor` 根据 `intent` 执行业务动作。
4. 设备控制类指令会查询目标房间和设备，校验设备能力和参数范围。
5. 设备状态变化写入 `devices`，并同步写入 `device_status_history`。
6. 提醒指令写入 `reminders`；天气指令优先查询 Open-Meteo，失败时读取本地备用天气；场景指令读取 `scene_actions` 批量修改设备。
7. 无论成功或失败，均写入 `command_logs`。
8. 接口返回统一响应结构，成功时包含解析结果和执行结果，失败时包含错误码和错误信息。

## 可用于测试报告的测试点

- 用户注册成功后密码不是明文。
- 用户登录成功返回 JWT，错误账号或密码拒绝登录。
- 未携带 JWT 访问受保护接口返回 `UNAUTHORIZED`。
- 查询房间、设备和 dashboard 返回初始化数据。
- 修改设备状态后数据库持久化，且写入设备状态历史。
- 中文指令解析覆盖开关、温度、亮度、音量、状态查询、场景、提醒和天气。
- 口语化表达、中文数字参数、设备别名和少量识别误差可被解析。
- 解析结果包含 `confidence`、`intent_scores`、关键词匹配和参数抽取详情。
- 中文指令执行后写入 `command_logs`。
- 设备控制指令写入 `device_status_history`。
- 温度、亮度、音量越界返回 `VALUE_OUT_OF_RANGE`。
- 不存在房间返回 `ROOM_NOT_FOUND`，不存在设备返回 `DEVICE_NOT_FOUND`。
- 不支持的设备操作返回 `UNSUPPORTED_ACTION`。
- 提醒 CRUD 可用，但不触发后台通知。
- 天气接口优先使用 Open-Meteo，失败或无网络时自动回退本地备用数据。
- 场景执行会按 `scene_actions` 批量修改设备。

## 可用于软件设计文档的架构说明

系统采用分层后端结构：

- 表现层：FastAPI 路由负责 HTTP 请求、鉴权依赖和统一响应。
- 业务层：服务类负责中文指令解析、指令执行、设备状态修改、场景执行、真实天气查询和本地备用天气。
- 数据访问层：SQLAlchemy ORM 负责 SQLite 数据持久化。
- 安全层：PBKDF2-SHA256 保存密码哈希，JWT 负责业务接口鉴权。

核心设计约束：

- 后端只接收中文文本，不处理音频。
- 设备为数据库虚拟设备，不接入真实硬件。
- 天气优先使用 Open-Meteo，失败时自动回退本地备用数据，测试不依赖真实外网。
- 提醒只做数据 CRUD，不引入后台定时任务。
- 所有核心业务接口尽量统一返回 `success/code/message/data`。

## 可用于项目管理文档的后端任务拆分

- 第 1 阶段：项目骨架、数据库模型、SQLite 初始化数据、健康检查。
- 第 2 阶段：用户认证、JWT 鉴权、房间设备查询、设备状态修改和 dashboard。
- 第 3 阶段：规则式中文指令解析和解析接口测试。
- 第 4 阶段：中文指令执行、指令日志、设备状态历史、提醒、天气、场景。
- 第 5 阶段：全局检查、测试补全、README 和交付文档整理。

建议分工：

- 后端接口与数据库：负责 FastAPI、SQLAlchemy、业务接口和测试。
- 前端语音与页面：负责 Vue 3、Web Speech API、页面展示和接口调用。
- 测试与文档：负责测试用例整理、测试报告、需求分析和设计文档。
- 项目管理：负责阶段计划、任务拆分、进度跟踪和最终汇报材料。
