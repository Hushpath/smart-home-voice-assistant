# AGENTS.md

本文件适用于 `frontend/`。详细页面、接口和演示说明见 `frontend/README.md`，这里只保留前端维护边界。

## 前端职责

前端使用 Vue 3 + Vite，负责登录、Dashboard、设备、语音控制、日志展示、提醒、场景和天气页面。

语音页保留三种输入路径：

- MediaRecorder 录音上传到 `POST /api/voice/execute`。
- Web Speech API 识别文本后调用 `POST /api/commands/execute`。
- 文本输入直接调用 `POST /api/commands/execute`。

前端不做方言归一、多指令拆分、指令解析或云端 ASR 厂商调用。

## 优先查看

- `frontend/README.md`
- `backend/README.md`
- `src/api/`
- `src/utils/normalizers.js`
- `src/views/VoiceControlView.vue`
- `src/views/LogsView.vue`
- `src/components/LogDetailDrawer.vue`

后端是接口字段和业务规则的事实来源；字段变化时同步适配 normalizer 和文档。

## 维护边界

- 所有请求通过 `src/api/` 和 Axios 封装，不在页面中散落硬编码 URL。
- 受保护接口必须自动携带 `Authorization: Bearer <token>`。
- token 缺失或失效时跳转登录页。
- 后端返回 `success === false` 时展示 `message`。
- 网络失败或后端不可用时给出友好提示。
- 页面字段必须经过适配，避免出现 `undefined`、`null null` 或 `[object Object]`。
- 保持现有深色智能家居风格，不重做整个视觉方向。
- 默认不要修改 `backend/`；确需修复时保持最小改动并说明影响。

## 语音页要求

- 不让前端直连云端 ASR。
- 不在前端保存或硬编码 ASR API Key、Secret、App ID；配置窗口只能提交给后端保存。
- 不把云端 ASR 作为唯一入口；未配置时提示使用浏览器识别或文本输入。
- 不让用户在每次执行前临时选择方言；默认方言通过个性化设置加载并交给后端偏好逻辑处理。
- 个性化设置、自动学习建议、设备别名和常用指令必须通过 `src/api/personalization.js` 调用 `/api/user/*`，不要在页面里散落 URL。
- Speech Synthesis 使用前端本地摘要文本，不依赖后端个性化播报字段。
- 主流程展示“听取指令、理解语音、执行控制、完成反馈”。
- 主界面只展示执行摘要；transcript、normalized_text、dialect_matches、intent_scores、raw JSON 放到日志详情。
- 批量执行结果只展示总体成功/失败和子指令简短结果。
- 保留 Speech Synthesis 播报开关。

## 日志页要求

- 日志列表展示摘要。
- 日志详情分块展示链路概览、语音识别、方言容错、指令解析、批量执行、执行信息和原始 JSON。
- 日志详情需要展示个性化命中信息：`preference_used` 和 `alias_match`。
- 字段缺失时显示 `-`。

## 常用命令

```bash
cd frontend
npm install
npm run dev
npm run build
```

仅修改文档时不强制运行构建，但最终说明中要写明原因。
