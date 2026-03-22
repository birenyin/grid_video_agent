# 电网视频生成智能体

这是一个基于 `Python 3.11 + FastAPI + React` 的本地项目，用来把电网新闻、电网知识科普、网页正文和 RPA 收稿内容自动转成短视频生产任务。

当前已经打通的链路：

1. 输入正文、现成脚本、网页链接或本地 RPA feed。
2. 生成摘要、播报稿、分镜和镜头提示词。
3. 生成中文配音、字幕、镜头图和镜头视频。
4. 合成最终成片并导出发布素材。
5. 在 React 工作台里逐镜头修改文案、提示词、参考图和渲染配置。
6. 创建自动任务，定时抓站点、自动建项目、自动渲染。

## 项目结构

- `app/`: FastAPI 后端、Provider、服务编排和静态资源托管。
- `frontend/`: React + Vite 前端工程。
- `runtime/`: 每个项目与自动任务的输出目录。
- `scripts/`: 启动、构建、案例运行和自动任务脚本。
- `tests/`: 后端接口和工作流回归测试。

## 已有接口

项目接口：

- `POST /projects/create_from_text`
- `POST /projects/create_from_script`
- `POST /projects/create_from_url`
- `POST /projects/create_from_rpa_feed`
- `PUT /projects/{project_id}/workflow/script`
- `POST /projects/{project_id}/workflow/images`
- `POST /projects/{project_id}/workflow/render`
- `GET /projects`
- `GET /projects/{project_id}`

自动任务接口：

- `POST /automation/jobs`
- `GET /automation/jobs`
- `GET /automation/jobs/{job_id}`
- `POST /automation/jobs/{job_id}/run`
- `POST /automation/jobs/{job_id}/status`

## Web 工作台

后端启动后打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

当前首页是 React 工作台，操作方式接近“剪映式分步流程”：

1. 左侧选项目和镜头。
2. 中间预览当前镜头、最终成片或 RPA 预览。
3. 右侧按“文案 / 画面 / 角色 / 配音 / 音乐 / 输出”分步编辑。
4. 可逐镜头修改文案和参考图，也可以直接一键成片。
5. 渲染失败、fallback 和最近错误会直接在工作台里显示。

## 环境准备

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_aicoding.ps1
```

## 启动后端

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_server.ps1
```

如需热重载：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_server.ps1 -Reload
```

## 构建 React 前端

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\build_frontend.ps1
```

这会在 `app/web/dist/` 下生成生产构建。FastAPI 检测到 `dist` 目录后，会优先服务 React 构建产物。

如果你改了前端但浏览器还是旧页面，通常只需要：

1. 重新执行一次 `build_frontend.ps1`
2. 重启 API 服务
3. 浏览器强刷

## 前端开发模式

需要单独跑 Vite 开发服务器时：

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\run_frontend_dev.ps1
```

默认地址：

- `http://127.0.0.1:5173`

Vite 已经代理 `/projects`、`/automation`、`/runtime` 和 `/health` 到本地 FastAPI。

## 自动任务说明

自动任务会按配置执行：

1. 抓取内置电网站点。
2. 生成 `fetched_feed.json`。
3. 基于 feed 自动建项目。
4. 按任务配置自动渲染。
5. 记录运行历史和最近一次生成的项目。

自动任务输出目录：

- `runtime/automation_runs/<job_id>/<timestamp>/`

手动触发某个自动任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_automation_job_now.ps1 -JobId <job_id>
```

## 关键配置

复制 `.env.example` 为 `.env` 后填写：

- `LLM_API_KEY`
- `VOLCENGINE_AK`
- `VOLCENGINE_SK`
- `VOLCENGINE_TTS_APPID`
- `VOLCENGINE_TTS_TOKEN`
- `VOLCENGINE_VIDEO_TEXT_REQ_KEY`
- `VOLCENGINE_VIDEO_IMAGE_REQ_KEY`
- `VOLCENGINE_VIDEO_USE_OPERATOR`
- `DOUYIN_CLIENT_KEY`
- `DOUYIN_CLIENT_SECRET`

自动任务相关配置：

- `AUTOMATION_SCHEDULER_ENABLED=true`
- `AUTOMATION_POLL_SECONDS=30`

推荐即梦视频 OpenAPI 配置：

- `VOLCENGINE_VIDEO_TEXT_REQ_KEY=jimeng_t2v_v30_1080p`
- `VOLCENGINE_VIDEO_IMAGE_REQ_KEY=jimeng_i2v_first_v30_1080`
- `VOLCENGINE_VIDEO_USE_OPERATOR=false`

默认人物参考图：

- `F:\AICODING\需求\电网人物形象.png`

当前前端会在用户不上传参考图时，默认沿用这张图。

## RPA Feed 示例

```json
{
  "items": [
    {
      "source": "国家电网官网",
      "title": "示例标题",
      "summary": "示例摘要",
      "published_at": "2026-03-22 09:00:00",
      "url": "https://example.com/article",
      "tags": ["调度", "保供"]
    }
  ]
}
```

## 测试

```powershell
cd F:\AICODING\电网视频生成助手
conda run -n AICODING python -m pytest -q
```

当前回归结果：

- `32 passed`

## 产物目录

默认写入：

- `runtime/<project_id>/`

常见产物：

- `summary.json`
- `script.json`
- `storyboard.json`
- `images/`
- `shots/`
- `audio/`
- `subtitles/`
- `final_video.mp4`
- `publish/publish_payload.json`
- `newsroom/`

## 后续建议

建议下一步继续做这几件事：

1. 把 React 工作台再封装成 Electron 或 Tauri 桌面版。
2. 给自动任务补企业微信或钉钉通知。
3. 给失败镜头做“关键镜头优先重试”策略。
4. 接抖音 / 视频号发布环节。
