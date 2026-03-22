# 电网视频生成智能体

这是一个基于 `Python 3.11 + FastAPI` 的本地可运行项目，用来把电网新闻、电网知识稿件、网页正文和 RPA 收稿内容自动转成短视频生产任务。

当前已经打通的链路：

1. 输入正文、脚本、网页链接或本地 RPA feed
2. 生成摘要、播报稿、分镜和镜头提示词
3. 生成中文配音、字幕、镜头图和镜头视频
4. 合成最终视频
5. 导出发布素材
6. 在 Web 控制台里查看项目、日志和产物
7. 自动抓站点并按频率自动建项目、自动渲染

## 已有接口

项目接口：

- `POST /projects/create_from_text`
- `POST /projects/create_from_script`
- `POST /projects/create_from_url`
- `POST /projects/create_from_rpa_feed`
- `POST /projects/{project_id}/render`
- `GET /projects`
- `GET /projects/{project_id}`

自动任务接口：

- `POST /automation/jobs`
- `GET /automation/jobs`
- `GET /automation/jobs/{job_id}`
- `POST /automation/jobs/{job_id}/run`
- `POST /automation/jobs/{job_id}/status`

## Web 控制台

启动服务后打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

控制台支持：

- 正文建项目
- 脚本建项目
- 网页抓取建项目
- RPA feed 建项目
- 项目渲染与产物预览
- 自动抓站点任务创建、暂停、恢复、立即执行

## 环境准备

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_aicoding.ps1
```

## 启动服务

```powershell
cd F:\AICODING\电网视频生成助手
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_server.ps1
```

默认地址：

- `http://127.0.0.1:8000`

如果确实要热重载：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_server.ps1 -Reload
```

## 自动任务说明

自动任务会按配置执行：

1. 抓取内置电网站点
2. 生成 `fetched_feed.json`
3. 基于 feed 自动建项目
4. 按任务配置自动渲染
5. 记录运行历史和最近一次生成的项目

自动任务运行目录：

- `runtime/automation_runs/<job_id>/<timestamp>/`

如果你想手动触发某个自动任务，也可以：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_automation_job_now.ps1 -JobId <job_id>
```

## 关键配置

把 `.env.example` 复制成 `.env` 后填写：

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

推荐视频 OpenAPI 配置：

- `VOLCENGINE_VIDEO_TEXT_REQ_KEY=jimeng_t2v_v30_1080p`
- `VOLCENGINE_VIDEO_IMAGE_REQ_KEY=jimeng_i2v_first_v30_1080`
- `VOLCENGINE_VIDEO_USE_OPERATOR=false`

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

- `27 passed`

## 产物目录

项目产物默认写入：

- `runtime/<project_id>/`

通常包含：

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

## 下一步建议

建议继续做这几件事：

1. 把 RPA 收稿直接落地为标准 feed JSON
2. 给自动任务补企业微信或钉钉通知
3. 给即梦失败镜头做关键镜头优先重试
4. 接 Douyin / 视频号发布环节
