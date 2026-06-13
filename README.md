# 智能家居语音交互助手系统

本项目是《软件工程》课程大作业，使用 Web 应用形式实现智能家居语音交互。前端负责页面展示和浏览器语音识别，后端负责用户认证、中文指令解析与执行、虚拟设备控制、提醒管理、天气查询、场景联动和操作日志。

## 功能特性

- 用户注册、登录、JWT 鉴权和当前用户查询。
- Dashboard 展示房间、设备、天气、场景和最近指令日志。
- 房间与设备查询，支持设备手动开关和状态历史查看。
- 中文指令解析与执行，支持设备控制、状态查询、场景执行、提醒创建和天气查询。
- 语音控制页支持浏览器 Web Speech API，也保留文本输入兜底。
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
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── data/
│   ├── docs/
│   ├── tests/
│   ├── requirements.txt
│   ├── run.py
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── config/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── utils/
│   │   └── views/
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
└── README.md
```

## 快速开始

### 从零运行步骤

拉取仓库后，在项目根目录依次执行以下步骤。

1. 安装后端依赖并初始化数据库：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.db.init_db
```

2. 启动后端服务：

```bash
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

3. 新开一个终端，安装并启动前端：

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

4. 浏览器访问前端地址，并使用默认账号登录。

## 默认账号

```text
用户名：testuser
密码：test123456
```

## 常用命令

后端：

```bash
cd backend
python -m app.db.init_db
python run.py
python -m pytest
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
- `/voice`：语音控制和文本指令执行。
- `/logs`：指令执行日志。
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
- `GET /api/reminders`
- `POST /api/reminders`
- `PATCH /api/reminders/{reminder_id}`
- `DELETE /api/reminders/{reminder_id}`
- `GET /api/scenes`
- `POST /api/scenes/{scene_id}/run`

成功响应格式：

```json
{
  "success": true,
  "code": "OK",
  "message": "操作成功",
  "data": {}
}
```

错误响应格式：

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "错误信息",
  "data": null
}
```

## 语音指令示例

- 打开客厅灯
- 关闭卧室空调
- 把卧室空调调到26度
- 将客厅灯亮度调到80
- 把电视音量调到30
- 查看客厅设备状态
- 开启睡眠模式
- 开启回家模式
- 开启离家模式
- 提醒我晚上八点吃药
- 提醒我20:00吃药
- 查询今天的天气
- 查询北京天气

鲁棒性示例：

- 开一下客厅电灯
- 帮我打开客厅灯
- 客厅灯开一下
- 把卧室空调调到二十六度
- 将客厅灯亮度调到八十
- 把电视机音量调到三十
- 打开客厅等
- 卧室冷气调到二十六度

## 鲁棒语音指令解析算法

后端不处理音频文件，只处理浏览器识别后的中文文本。解析流程为：

```text
语音输入 -> 识别文本 -> 文本标准化 -> 同义词归一 -> 中文数字转换 -> 意图打分 -> 房间/设备匹配 -> 参数校验 -> 置信度计算 -> 指令执行
```

当前解析能力包括：

- 文本标准化：去除常见标点和口语词，例如“请”“帮我”“麻烦”“一下”。
- 同义词归一：开启/启动/开一下归一为打开，冷气归一为空调，电视机归一为电视，声音归一为音量。
- 中文数字转换：二十六、八十、三十等可转换为数字参数，晚上八点可解析为 `20:00`。
- 意图打分：根据动作词、设备词、房间词、数值词和单位词计算各意图得分。
- 模糊匹配：优先精确匹配，再做别名匹配，最后用轻量字符串相似度处理少量识别误差。
- 参数校验：温度范围 `16-30`，亮度和音量范围 `0-100`，越界不会执行。
- 置信度输出：解析结果包含 `confidence`、`matched_keywords`、`match_type` 和 `parse_detail`，日志详情可查看完整解析过程。

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
- `reminders`
- `scenes`
- `scene_actions`

初始化数据包括 1 个默认家庭、4 个房间、11 个设备、3 个场景和 1 个默认测试用户。

## 天气功能

天气接口：

```text
GET /api/weather?city=北京
```

支持城市示例：

- 北京
- 上海
- 广州
- 深圳
- 杭州
- 南京
- 成都
- 重庆
- 西安
- 武汉

天气数据优先使用 Open-Meteo。外部请求失败、超时或城市无法识别时，后端会返回本地备用数据，并在返回字段中标记 `source: "mock"`。

## 测试

运行后端测试：

```bash
cd backend
python -m pytest
```

运行前端构建检查：

```bash
cd frontend
npm run build
```

## 已知限制

- 系统使用 SQLite 中的虚拟设备，不接入真实智能家居硬件。
- 后端只接收前端识别后的中文文本，不处理音频文件。
- 语音识别依赖浏览器 Web Speech API 支持。
- 提醒模块只支持数据管理，不包含后台通知或定时推送。
- 天气查询依赖外网时可能失败，但会自动回退本地备用数据，保证演示稳定。

## 相关文档

- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 软件工程文档支撑材料：[backend/docs/software_engineering_support.md](backend/docs/software_engineering_support.md)
