# AGENTS.md

## 适用范围

本文件适用于 `backend/` 目录。当前后端已经完成主要功能开发，后续工作应以维护、修复、测试补全和文档同步为主，不再按阶段开发提示执行。

## 项目定位

本项目是《软件工程》课程大作业“智能家居语音交互助手系统”的后端部分。

后端使用 FastAPI 接收前端识别后的中文文本指令，负责：

- 用户认证和 JWT 鉴权；
- 房间、设备和 dashboard 数据接口；
- 设备状态持久化和设备状态历史；
- 中文指令解析与执行；
- 指令执行日志；
- 提醒事项 CRUD；
- 场景查询和场景执行；
- 天气查询，优先使用 Open-Meteo，失败时回退本地备用数据。

系统使用数据库中的虚拟设备模拟智能家居设备，不接入真实硬件。

## 技术栈

- Python 3.10+
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- JWT
- pytest
- Uvicorn
- httpx

不要引入 Spring Boot、Django、MySQL、Redis、Docker、Celery、APScheduler、外部大模型 API 或真实智能家居硬件接入，除非用户明确要求并说明原因。

## 事实来源

修改后端前，应优先查看：

1. `backend/README.md`
2. `backend/app/routers/`
3. `backend/app/schemas/`
4. `backend/app/models/`
5. `backend/app/services/`
6. Swagger 文档 `/docs`

如果文档与代码不一致，以当前代码和测试为准，并同步修正文档。

## 维护原则

- 保持现有接口路径稳定，不随意改动 `/api/...` 路由。
- 保持统一响应格式：`success/code/message/data`。
- 保持现有数据库模型稳定，不随意重建表结构。
- 保持默认账号、初始化数据和课程演示流程可用。
- 修改设备状态时必须持久化到 SQLite。
- 设备状态变化必须写入 `device_status_history`。
- 指令执行成功或失败都必须写入 `command_logs`。
- 密码必须哈希存储，不能明文存储。
- 提醒模块只做 CRUD，不实现后台定时推送、系统通知、消息队列或长期后台任务。
- 天气请求必须有超时和本地兜底，测试不能依赖真实外网。

## 鲁棒语音指令解析维护约定

中文指令解析是本项目的核心能力，主要位于 `app/services/command_parser.py`、`app/services/command_executor.py` 和 `app/routers/commands.py`。维护时应保留以下设计：

- 后端只接收前端识别后的中文文本，不接收音频文件，不训练语音识别模型。
- 不接入外部 ASR 服务、外部大模型 API 或大型 NLP 依赖。
- `/api/commands/parse` 和 `/api/commands/execute` 路径、请求体字段 `{ "command": "..." }` 和统一响应格式必须保持稳定。
- 解析结果应继续包含 `original_text`、`normalized_text`、`intent`、`room`、`device_type`、`value`、`confidence`、`matched_keywords`、`match_type`、`parse_detail`、`valid` 和 `message` 等字段。
- `parse_detail` 应承载可解释算法过程，包括 `intent_scores`、`room_match`、`device_match`、`value_extract`、`time_extract` 或等价信息。
- 文本标准化应继续支持口语词弱化、同义词归一、中文数字转换和常见标点处理。
- 意图识别应保持可解释打分机制，不要退回到不可解释的大段 if-else。
- 房间和设备匹配应优先精确匹配，其次别名匹配，最后使用轻量字符串相似度模糊匹配。
- 温度范围保持 `16-30`，亮度和音量范围保持 `0-100`；越界返回 `VALUE_OUT_OF_RANGE`，不得执行设备状态修改。
- 低置信度设备控制类指令不得强行执行，应返回明确提示。
- 指令执行成功或失败都必须将增强后的解析信息写入 `command_logs.parsed_result`。
- 设备状态变化仍必须写入 `device_status_history`。
- 修改解析规则后，应优先补充或更新 `tests/test_command_parse.py` 和 `tests/test_command_execute.py`。

建议保留的演示/测试指令：

- `打开客厅灯`
- `开一下客厅电灯`
- `帮我打开客厅灯`
- `客厅灯开一下`
- `把卧室空调调到二十六度`
- `将客厅灯亮度调到八十`
- `把电视机音量调到三十`
- `打开客厅等`
- `卧室冷气调到二十六度`
- `开启睡眠模式`
- `提醒我晚上八点吃药`
- `查询今天的天气`

## 鉴权规则

除以下接口外，其余业务接口默认需要 JWT：

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/weather`

如果因前端联调需要调整鉴权，必须保持最小修改，并在 README 中说明原因。

## 常用命令

安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

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

或：

```bash
cd backend
uvicorn app.main:app --reload
```

运行测试：

```bash
cd backend
python -m pytest
```

## 修改后检查

后端代码修改后，至少检查：

- `python -m pytest` 是否通过；
- `GET /api/health` 是否可用；
- `/docs` 是否能打开；
- README 中的接口、字段、启动命令是否仍准确；
- 是否影响前端已对接字段。

仅修改文档时不强制运行测试，但需要说明未运行测试的原因。

## 与前端的协作约定

前端位于 `frontend/`，默认通过 Vite `/api` 代理访问后端。后端是接口字段和业务规则的事实来源；如果后端字段发生变化，必须同步更新前端适配函数和相关 README。

不要为了前端展示方便伪造后端数据或重写既有接口。确需修复 CORS、接口注册或明显 bug 时，应保持最小改动并说明影响范围。
