import { DEFAULT_REFERENCE_HINT, getProjectTitle } from "../helpers";
import { EmptyState } from "./Shared";

function getProjectInitial(title) {
  const clean = String(title || "").trim();
  if (!clean) return "?";
  return clean.slice(0, 1).toUpperCase();
}

export function ProjectSidebar({
  busy,
  collapsed,
  projectList,
  selectedProjectId,
  projectDetail,
  onSelectProject,
  onOpenCreate,
  onOpenAutomation,
  onToggleCollapse,
}) {
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
      <section className="glass-card sidebar-section">
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
            projectList.map((item) => (
              <button
                key={item.project_id}
                type="button"
                className={`project-list-card ${selectedProjectId === item.project_id ? "active" : ""}`}
                disabled={busy}
                onClick={() => onSelectProject(item.project_id)}
              >
                <div className="project-list-head">
                  <strong>{item.title}</strong>
                  <span className={`soft-chip ${item.status === "rendered" ? "ok" : item.status === "failed" ? "danger" : ""}`}>
                    {item.status}
                  </span>
                </div>
                <p>{item.project_id}</p>
                <div className="meta-chip-row">
                  <span className="soft-chip">{item.mode}</span>
                  <span className="soft-chip">{item.source_type}</span>
                  <span className="soft-chip">{item.shot_count} 镜头</span>
                </div>
              </button>
            ))
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
