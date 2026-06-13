# AGENTS.md

## 适用范围

本文件适用于 `frontend/` 目录。当前前端已经完成主要页面和后端联调，后续工作应以维护、修复、样式微调、字段适配和文档同步为主，不再按阶段开发提示执行。

## 项目定位

本目录是《软件工程》课程大作业“智能家居语音交互助手系统”的前端部分。

前端使用 Vue 3 + Vite 实现 Web 管理界面，负责：

- 登录和认证状态管理；
- Dashboard 系统概览；
- 房间与设备展示；
- 设备手动控制和设备历史查看；
- 浏览器 Web Speech API 语音识别；
- 中文指令解析、执行和结果展示；
- 操作日志展示；
- 提醒管理；
- 场景模式执行；
- 天气展示和城市切换。

后端位于 `backend/`，是接口路径、请求字段、响应字段和业务规则的事实来源。

## 技术栈

- Vue 3
- Vite
- JavaScript
- Element Plus
- Axios
- Vue Router
- Pinia
- 浏览器 Web Speech API

不要引入 React、Angular、Next.js、Nuxt、TypeScript、外部语音识别 API、外部大模型 API、真实智能家居硬件接口、复杂 3D 或移动 App/PWA 级改造，除非用户明确要求。

## 事实来源

修改接口调用或字段展示前，应优先查看：

1. `frontend/README.md`
2. `backend/README.md`
3. `backend/app/routers/`
4. `backend/app/schemas/`
5. `backend/app/models/`
6. `frontend/src/api/`
7. `frontend/src/utils/normalizers.js`

如果 README 与代码不一致，以当前代码和后端实际接口为准，并同步修正文档。

## 维护原则

- 优先适配现有后端，不随意修改后端接口路径。
- 所有请求应通过 `src/api/` 和 Axios 封装，不在页面中散落硬编码 URL。
- 后端地址集中配置在 `src/config/api.js` 或 Vite 代理中。
- 受保护接口必须自动携带 `Authorization: Bearer <token>`。
- token 缺失或失效时应跳转登录页。
- 后端返回 `success === false` 时应展示 `message`。
- 后端未启动或网络失败时应给出友好提示。
- 页面字段必须通过适配函数兼容后端返回，避免出现大量 `undefined`。
- 保持当前深色智能家居控制台风格，不大幅改换视觉方向。
- 桌面端课堂演示优先，窄屏只需基础可用。

## 语音解析展示维护约定

前端语音输入依赖浏览器 Web Speech API，后端负责对识别后的中文文本做鲁棒指令解析。维护语音页、日志页或命令适配函数时，应保持以下约定：

- 不接入外部语音识别 API、外部大模型 API 或真实硬件接口。
- `POST /api/commands/parse` 和 `POST /api/commands/execute` 请求体保持 `{ "command": "..." }`。
- 命令相关字段必须通过 `src/utils/normalizers.js` 适配，避免页面直接假设所有字段一定存在。
- `normalizeParsedCommand()` 应兼容 `original_text`、`normalized_text`、`confidence`、`matched_keywords`、`match_type`、`parse_detail` 等后端字段。
- 语音控制页只展示用户友好的简化摘要：原始/标准化文本、意图、房间、设备、参数、置信度、执行 message、执行前后状态。
- 语音控制页默认不要堆满完整 `intent_scores`、`parse_detail` 或大段 raw JSON；完整算法过程放到折叠详情或日志详情。
- 置信度展示不应伪造，只使用后端返回的 `confidence`；低于 `0.6` 时提示用户换一种说法或使用文本输入。
- 操作日志页应保留“详情”入口，用于展示完整解析过程、执行结果和 raw JSON，支撑课程演示、测试报告和软件设计文档截图。
- 推荐指令应同时包含标准表达和少量鲁棒性示例，例如 `开一下客厅电灯`、`把卧室空调调到二十六度`、`打开客厅等`、`卧室冷气调到二十六度`。

## 后端修改边界

默认不要修改 `backend/`。只有以下情况可以做最小后端修复：

- CORS 或代理配置导致前端无法联调；
- 接口未正确注册；
- README 与实际启动命令明显不一致；
- 前后端联调发现明显 bug；
- 必要错误处理缺失，导致页面无法稳定演示。

禁止为了前端方便重构后端目录、改接口路径、改统一响应格式、重设数据库模型、删除鉴权、删除测试或伪造后端数据。

如果修改了 `backend/`，完成说明中必须单独写明原因、文件和影响范围。

## 常用命令

安装依赖：

```bash
cd frontend
npm install
```

启动前端：

```bash
cd frontend
npm run dev
```

构建检查：

```bash
cd frontend
npm run build
```

默认前端地址：

```text
http://127.0.0.1:5173
```

默认后端地址：

```text
http://127.0.0.1:8000
```

## 修改后检查

前端代码修改后，至少检查：

- `npm run build` 是否通过；
- 登录页是否可打开；
- 登录后是否能进入 Dashboard；
- 受保护接口是否携带 token；
- Dashboard、设备、语音、日志、提醒、场景页面是否仍可访问；
- 与修改相关的接口字段是否经过 `normalizers.js` 适配；
- `frontend/README.md` 是否需要同步更新。

仅修改文档时不强制运行构建，但需要说明未运行构建的原因。

## 演示稳定性

系统用于课程演示、截图和录屏。修改时优先保证：

- 默认账号可登录；
- Dashboard 可展示统计和天气；
- 设备可手动控制并查看历史；
- 语音页可用文本兜底执行指令；
- 日志、提醒和场景页面可正常展示；
- 后端不可用时页面不崩溃。
