import { DEFAULT_REFERENCE_HINT, getProjectTitle } from "../helpers";
import { EmptyState } from "./Shared";

function getProjectInitial(title) {
  const clean = String(title || "").trim();
  if (!clean) return "?";
  return clean.slice(0, 1).toUpperCase();
}

function describeSourceType(sourceType) {
  if (sourceType === "rpa_feed") return "自动抓取";
  if (sourceType === "manual_script") return "脚本导入";
  if (sourceType === "url") return "网页抓取";
  return sourceType || "手动创建";
}

function formatProjectTime(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function ProjectSidebar({
  busy,
  collapsed,
  projectList,
  automationJobs,
  automationJobDetails,
  selectedProjectId,
  projectDetail,
  onSelectProject,
  onOpenCreate,
  onOpenAutomation,
  onToggleCollapse,
}) {
  function findAutomationContext(projectId) {
    const linkedJob = (automationJobs || []).find((job) => job.last_project_id === projectId);
    if (!linkedJob) {
      return null;
    }

    const runs = automationJobDetails?.[linkedJob.job_id]?.runs || [];
    const latestRun = runs[0] || null;
    return { linkedJob, latestRun };
  }

  function buildProjectStage(item, automationContext) {
    if (item.status === "rendering") {
      return {
        label: "自动渲染中",
        tone: "warn",
        detail: automationContext?.linkedJob
          ? `任务 ${automationContext.linkedJob.name} 正在生成视频`
          : "项目正在生成音频、字幕或成片",
      };
    }

    if (item.status === "rendered") {
      return {
        label: automationContext?.linkedJob ? "自动任务已完成" : "成片已输出",
        tone: "ok",
        detail: automationContext?.latestRun
          ? `最近抓取 ${automationContext.latestRun.fetched_item_count} 条`
          : "可以直接打开查看最终视频",
      };
    }

    if (item.status === "draft" && item.source_type === "rpa_feed") {
      return {
        label: automationContext?.linkedJob?.render?.auto_render ? "已抓取待渲染" : "抓取草稿",
        tone: "info",
        detail: automationContext?.latestRun
          ? `已抓取 ${automationContext.latestRun.fetched_item_count} 条，可先看文案和分镜`
          : "抓取内容已落成草稿项目，可直接编辑文案",
      };
    }

    if (item.status === "failed") {
      return {
        label: "处理失败",
        tone: "danger",
        detail: "可点进项目查看失败步骤和错误记录",
      };
    }

    return {
      label: "手动项目",
      tone: "info",
      detail: "可以继续修改文案、出图或渲染",
    };
  }

  if (collapsed) {
    return (
      <aside className="studio-sidebar collapsed">
        <section className="glass-card sidebar-section sidebar-section-compact">
          <div className="compact-sidebar-head">
            <button type="button" className="compact-icon-button" onClick={onToggleCollapse} title="展开项目库">
              ≡
            </button>
            <button type="button" className="compact-icon-button accent" onClick={onOpenCreate} title="新建项目">
              +
            </button>
            <button type="button" className="compact-icon-button" onClick={onOpenAutomation} title="自动任务">
              A
            </button>
          </div>

          <div className="compact-project-list">
            {projectList.length ? (
              projectList.map((item) => (
                <button
                  key={item.project_id}
                  type="button"
                  className={`project-mini-button ${selectedProjectId === item.project_id ? "active" : ""}`}
                  title={item.title}
                  disabled={busy}
                  onClick={() => onSelectProject(item.project_id)}
                >
                  <span>{getProjectInitial(item.title)}</span>
                  <small>{item.shot_count}</small>
                </button>
              ))
            ) : (
              <div className="compact-empty">空</div>
            )}
          </div>
        </section>
      </aside>
    );
  }

  return (
    <aside className="studio-sidebar">
      <section className="glass-card sidebar-section sidebar-projects">
        <div className="section-title-row">
          <div>
            <div className="section-label">Projects</div>
            <h2>项目库</h2>
          </div>
          <div className="meta-chip-row">
            <span className="count-pill">{projectList.length}</span>
            <button type="button" className="ghost-button slim" onClick={onToggleCollapse}>
              收起
            </button>
          </div>
        </div>

        <div className="sidebar-action-row">
          <button type="button" className="primary-button" onClick={onOpenCreate}>
            新建项目
          </button>
          <button type="button" className="ghost-button" onClick={onOpenAutomation}>
            自动任务
          </button>
        </div>

        <div className="project-list">
          {projectList.length ? (
            projectList.map((item) => {
              const automationContext = findAutomationContext(item.project_id);
              const stage = buildProjectStage(item, automationContext);

              return (
                <button
                  key={item.project_id}
                  type="button"
                  className={`project-list-card ${selectedProjectId === item.project_id ? "active" : ""} ${automationContext ? "automation-linked" : ""}`}
                  disabled={busy}
                  onClick={() => onSelectProject(item.project_id)}
                >
                  <div className="project-list-head">
                    <strong>{item.title}</strong>
                    <span className={`soft-chip ${item.status === "rendered" ? "ok" : item.status === "failed" ? "danger" : item.status === "rendering" ? "warn" : ""}`}>
                      {item.status}
                    </span>
                  </div>
                  <div className="project-card-ribbon-row">
                    <span className={`project-card-ribbon ${stage.tone}`}>{stage.label}</span>
                    {automationContext?.linkedJob ? (
                      <span className="soft-chip">自动任务</span>
                    ) : null}
                  </div>
                  <p>{item.project_id}</p>
                  <div className="meta-chip-row">
                    <span className="soft-chip">{item.mode}</span>
                    <span className="soft-chip">{describeSourceType(item.source_type)}</span>
                    <span className="soft-chip">{item.shot_count} 镜头</span>
                  </div>
                  <div className="project-card-summary">{stage.detail}</div>
                  {automationContext?.linkedJob ? (
                    <div className="small-copy">
                      自动任务：{automationContext.linkedJob.name}
                      {automationContext.latestRun ? ` · 最近抓取 ${automationContext.latestRun.fetched_item_count} 条` : ""}
                    </div>
                  ) : null}
                  <div className="small-copy">最近更新：{formatProjectTime(item.updated_at)}</div>
                </button>
              );
            })
          ) : (
            <EmptyState title="还没有项目" body="点上方“新建项目”就能开始，或者导入 RPA Feed。" compact />
          )}
        </div>
      </section>

      <section className="glass-card sidebar-section sidebar-summary-section">
        <div className="section-title-row">
          <div>
            <div className="section-label">Current</div>
            <h2>当前项目</h2>
          </div>
        </div>

        {projectDetail ? (
          <div className="project-summary-box">
            <strong>{getProjectTitle(projectDetail.project)}</strong>
            <div className="small-copy">状态：{projectDetail.project.status}</div>
            <div className="small-copy">
              {projectDetail.project.content_input.mode} · {projectDetail.project.content_input.aspect_ratio}
            </div>
            <div className="small-copy">镜头数量：{projectDetail.project.storyboard.length}</div>
            <div className="small-copy">
              默认参考图：{projectDetail.project.artifacts.resolved_reference_image_path || DEFAULT_REFERENCE_HINT}
            </div>
            <div className="callout compact">
              镜头时间线已经放到中间工作区，这里只保留项目切换和当前项目摘要，减少左右两边重复占位。
            </div>
          </div>
        ) : (
          <EmptyState title="先选一个项目" body="选中项目后，这里会显示当前项目摘要，镜头时间线在中间工作区。" compact />
        )}
      </section>
    </aside>
  );
}
