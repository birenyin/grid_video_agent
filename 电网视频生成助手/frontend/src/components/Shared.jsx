import { findShotImage, findShotVideo, normalizeRuntimeUrl } from "../helpers";

export function EmptyState({ title, body, compact = false }) {
  return (
    <div className={`empty-state-card ${compact ? "compact" : ""}`}>
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}

export function PanelCard({ eyebrow, title, actions, children }) {
  return (
    <section className="panel-card">
      <div className="panel-card-head">
        <div>
          {eyebrow ? <div className="panel-eyebrow">{eyebrow}</div> : null}
          <h3>{title}</h3>
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Field({ label, span = false, note, children }) {
  return (
    <label className={`field ${span ? "span-all" : ""}`}>
      <span className="field-label">{label}</span>
      {children}
      {note ? <span className="field-note">{note}</span> : null}
    </label>
  );
}

export function ShotPreviewCard({ projectDetail, selectedShot }) {
  if (!selectedShot) {
    return <EmptyState title="还没有选中镜头" body="从左侧时间线里点一个镜头，这里就会显示当前素材。" compact />;
  }

  const shotVideo = findShotVideo(projectDetail, selectedShot.shot_id);
  const shotImage = findShotImage(projectDetail, selectedShot.shot_id);
  const provider = shotVideo
    ? `${shotVideo.provider_name}${shotVideo.used_fallback ? " / fallback" : ""}`
    : shotImage
      ? `${shotImage.provider_name}${shotImage.used_fallback ? " / fallback" : ""}`
      : "待生成";
  const previewUrl = shotVideo
    ? normalizeRuntimeUrl(shotVideo.poster_path || shotVideo.video_path)
    : shotImage
      ? normalizeRuntimeUrl(shotImage.image_path)
      : "";

  return (
    <div className="shot-preview-card">
      <div className="shot-preview-head">
        <strong>镜头 {selectedShot.shot_id}</strong>
        <span className="soft-chip">{provider}</span>
      </div>
      {previewUrl ? (
        <img src={previewUrl} alt={`shot-${selectedShot.shot_id}`} className="shot-preview-image" />
      ) : (
        <div className="shot-preview-image placeholder">当前镜头还没有可用画面</div>
      )}
    </div>
  );
}
