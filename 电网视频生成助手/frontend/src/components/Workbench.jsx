import { EmptyState } from "./Shared";

export function Workbench({
  busy,
  projectDetail,
  preview,
  previewMode,
  onPreviewModeChange,
  workflowStep,
  onWorkflowStepChange,
  diagnostics,
  selectedShotId,
  onSelectShot,
  onRunOneClick,
}) {
  const shots = projectDetail?.project?.storyboard || [];

  return (
    <main className="studio-workbench">
      <section className="glass-card workbench-shell">
        <div className="workbench-topbar">
          <div>
            <div className="section-label">Workspace</div>
            <h1>{projectDetail ? projectDetail.project.summary?.title || projectDetail.project.content_input.title || projectDetail.project.project_id : "请选择项目"}</h1>
            {projectDetail ? (
              <div className="meta-chip-row roomy">
                <span className="soft-chip">{projectDetail.project.status}</span>
                <span className="soft-chip">{projectDetail.project.content_input.mode}</span>
                <span className="soft-chip">{projectDetail.project.content_input.aspect_ratio}</span>
                <span className="soft-chip">{projectDetail.project.content_input.source_type}</span>
                <span className="soft-chip">{shots.length} 镜头</span>
              </div>
            ) : null}
          </div>

          <div className="workbench-top-actions">
            <div className="pill-switch">
              <button
                type="button"
                className={`pill-button ${workflowStep === "script" ? "active" : ""}`}
                disabled={!projectDetail || busy}
                onClick={() => onWorkflowStepChange("script")}
              >
                1. 文案与分镜
              </button>
              <button
                type="button"
                className={`pill-button ${workflowStep === "images" ? "active" : ""}`}
                disabled={!projectDetail || busy}
                onClick={() => onWorkflowStepChange("images")}
              >
                2. 镜头图片
              </button>
              <button
                type="button"
                className={`pill-button ${workflowStep === "render" ? "active" : ""}`}
                disabled={!projectDetail || busy}
                onClick={() => onWorkflowStepChange("render")}
              >
                3. 最终成片
              </button>
            </div>

            <button type="button" className="primary-button" disabled={!projectDetail || busy} onClick={onRunOneClick}>
              一键成片
            </button>
          </div>
        </div>

        {projectDetail ? (
          <div className="editor-grid">
            <section className="timeline-panel">
              <div className="section-title-row">
                <div>
                  <div className="section-label">Timeline</div>
                  <h2>镜头列表</h2>
                </div>
                <div className="small-copy">可逐镜头修改文案和画面</div>
              </div>

              <div className="timeline-scroll">
                {shots.map((shot) => {
                  const isActive = selectedShotId === shot.shot_id;
                  const previewText = shot.subtitle_text || shot.narration_text || "暂无文案";
                  return (
                    <button
                      key={shot.shot_id}
                      type="button"
                      className={`timeline-row ${isActive ? "active" : ""}`}
                      disabled={busy}
                      onClick={() => onSelectShot(shot.shot_id)}
                    >
                      <div className="timeline-order">
                        <span>{String(shot.shot_id).padStart(2, "0")}</span>
                        <small>{shot.shot_duration}s</small>
                      </div>
                      <div className="timeline-copy">
                        <strong>{shot.shot_type}</strong>
                        <p>{previewText}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="stage-panel">
              <div className="stage-toolbar">
                <div className="pill-switch">
                  <button
                    type="button"
                    className={`pill-button ${previewMode === "shot" ? "active" : ""}`}
                    onClick={() => onPreviewModeChange("shot")}
                  >
                    当前镜头
                  </button>
                  <button
                    type="button"
                    className={`pill-button ${previewMode === "final" ? "active" : ""}`}
                    onClick={() => onPreviewModeChange("final")}
                  >
                    最终成片
                  </button>
                  <button
                    type="button"
                    className={`pill-button ${previewMode === "preview" ? "active" : ""}`}
                    onClick={() => onPreviewModeChange("preview")}
                  >
                    RPA 预览
                  </button>
                </div>
                <div className="stage-meta">
                  <span className="soft-chip">{preview.provider}</span>
                  <span className="soft-chip">{preview.duration}</span>
                </div>
              </div>

              <div className={`stage-frame ${preview.aspectRatio === "9:16" ? "portrait" : "landscape"}`}>
                {preview.kind === "video" ? (
                  <video src={preview.url} controls preload="metadata" className="stage-media" />
                ) : preview.kind === "image" ? (
                  <img src={preview.url} alt={preview.title} className="stage-media" />
                ) : (
                  <div className="stage-empty">
                    <strong>{preview.title}</strong>
                    <p>{preview.subtitle}</p>
                  </div>
                )}
              </div>

              <div className="stage-caption">
                <div>
                  <strong>{preview.title}</strong>
                  <p>{preview.subtitle}</p>
                </div>
              </div>

              <div className="diagnostic-grid">
                {diagnostics.map((item) => (
                  <article key={`${item.label}-${item.headline}`} className={`diagnostic-tile ${item.tone}`}>
                    <span className="section-label">{item.label}</span>
                    <strong>{item.headline}</strong>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>
        ) : (
          <EmptyState
            title="先从左侧选一个项目"
            body="新的 React 工作台已经接上分步流程，选中项目后就能像剪映一样逐镜头修改。"
          />
        )}
      </section>
    </main>
  );
}
