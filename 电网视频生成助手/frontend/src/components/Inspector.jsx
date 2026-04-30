import { DEFAULT_REFERENCE_HINT, INSPECTOR_TABS, findShotImage, findShotVideo } from "../helpers";
import { EmptyState, Field, PanelCard, ShotPreviewCard } from "./Shared";

function buildShotStatus(projectDetail, selectedShot) {
  if (!selectedShot) {
    return {
      summary: "未选择镜头",
      provider: "待选择",
      reference: projectDetail?.project?.artifacts?.resolved_reference_image_path || DEFAULT_REFERENCE_HINT,
      statusTone: "warning",
      mode: "等待操作",
    };
  }

  const shotImage = findShotImage(projectDetail, selectedShot.shot_id);
  const shotVideo = findShotVideo(projectDetail, selectedShot.shot_id);
  const reference =
    projectDetail?.project?.artifacts?.shot_reference_paths?.[String(selectedShot.shot_id)] ||
    projectDetail?.project?.artifacts?.resolved_reference_image_path ||
    DEFAULT_REFERENCE_HINT;

  if (shotVideo) {
    return {
      summary: "已有镜头视频",
      provider: `${shotVideo.provider_name}${shotVideo.used_fallback ? " / fallback" : ""}`,
      reference,
      statusTone: shotVideo.used_fallback ? "warning" : "success",
      mode: selectedShot.needs_real_material ? "真实素材优先" : "视频已可用",
    };
  }

  if (shotImage) {
    return {
      summary: "已有镜头图片",
      provider: `${shotImage.provider_name}${shotImage.used_fallback ? " / fallback" : ""}`,
      reference,
      statusTone: shotImage.used_fallback ? "warning" : "success",
      mode: selectedShot.needs_real_material ? "真实素材优先" : "待合成视频",
    };
  }

  return {
    summary: "还没有画面素材",
    provider: "待生成",
    reference,
    statusTone: "warning",
    mode: selectedShot.needs_real_material ? "真实素材优先" : "等待生成",
  };
}

export function Inspector({
  busy,
  projectDetail,
  selectedShot,
  inspectorTab,
  renderForm,
  artifactEntries,
  mediaItems,
  onTabChange,
  onProjectFieldChange,
  onShotFieldChange,
  onDefaultReferenceChange,
  onShotReferenceChange,
  onSaveScript,
  onRegenerateStoryboard,
  onGenerateCurrent,
  onGenerateAll,
  onGenerateCurrentVideo,
  onGenerateAllVideos,
  onRenderFieldChange,
  onRender,
}) {
  const project = projectDetail?.project;
  const shotReferencePath = selectedShot
    ? projectDetail?.project?.artifacts?.shot_reference_paths?.[String(selectedShot.shot_id)] || ""
    : "";
  const shotStatus = buildShotStatus(projectDetail, selectedShot);

  return (
    <aside className="studio-inspector">
      <section className="glass-card inspector-shell">
        <div className="section-title-row">
          <div>
            <div className="section-label">Inspector</div>
            <h2>分步工作流</h2>
          </div>
        </div>

        {projectDetail ? (
          <>
            <div className="inspector-tab-row">
              {INSPECTOR_TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`tab-button ${inspectorTab === tab.key ? "active" : ""}`}
                  disabled={busy}
                  onClick={() => onTabChange(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="inspector-context-card">
              <div className="inspector-context-head">
                <div>
                  <div className="section-label">Selected Shot</div>
                  <strong>{selectedShot ? `镜头 ${selectedShot.shot_id}` : "当前没有选中镜头"}</strong>
                </div>
                <span className={`soft-chip ${shotStatus.statusTone === "success" ? "ok" : shotStatus.statusTone === "warning" ? "warn" : ""}`}>
                  {shotStatus.summary}
                </span>
              </div>
              <div className="context-grid">
                <div className="context-item">
                  <span>类型</span>
                  <strong>{selectedShot?.shot_type || "待选择"}</strong>
                </div>
                <div className="context-item">
                  <span>时长</span>
                  <strong>{selectedShot ? `${selectedShot.shot_duration}s` : "--"}</strong>
                </div>
                <div className="context-item span-2">
                  <span>当前 Provider</span>
                  <strong>{shotStatus.provider}</strong>
                </div>
                <div className="context-item span-2">
                  <span>参考图</span>
                  <strong>{shotStatus.reference}</strong>
                </div>
                <div className="context-item span-2">
                  <span>生成策略</span>
                  <strong>{shotStatus.mode}</strong>
                </div>
              </div>
            </div>

            <div className="inspector-scroll">
              {inspectorTab === "script" ? (
                <>
                  <PanelCard
                    eyebrow="Step 1"
                    title="项目文案"
                    actions={
                      <>
                        <button type="button" className="ghost-button" disabled={busy} onClick={() => onSaveScript(false)}>
                          保存文案
                        </button>
                        <button type="button" className="primary-button" disabled={busy} onClick={onRegenerateStoryboard}>
                          重新拆分分镜
                        </button>
                      </>
                    }
                  >
                    <div className="form-grid">
                      <Field label="标题">
                        <input
                          value={project.summary?.title || project.content_input.title || ""}
                          onChange={(event) => onProjectFieldChange("title", event.target.value)}
                        />
                      </Field>
                      <Field label="模式">
                        <select value={project.content_input.mode} onChange={(event) => onProjectFieldChange("mode", event.target.value)}>
                          <option value="news_mode">news_mode</option>
                          <option value="explain_mode">explain_mode</option>
                        </select>
                      </Field>
                      <Field label="时长（秒）">
                        <input
                          type="number"
                          min="15"
                          max="150"
                          value={project.content_input.target_duration_seconds}
                          onChange={(event) => onProjectFieldChange("target_duration_seconds", Number(event.target.value))}
                        />
                      </Field>
                      <Field label="画幅">
                        <select
                          value={project.content_input.aspect_ratio}
                          onChange={(event) => onProjectFieldChange("aspect_ratio", event.target.value)}
                        >
                          <option value="9:16">9:16 竖屏</option>
                          <option value="16:9">16:9 横屏</option>
                        </select>
                      </Field>
                      <Field label="摘要" span>
                        <textarea
                          rows="4"
                          value={project.summary?.summary || ""}
                          onChange={(event) => onProjectFieldChange("summary", event.target.value)}
                        />
                      </Field>
                      <Field label="完整脚本" span>
                        <textarea
                          rows="8"
                          value={project.script?.full_script || project.content_input.raw_text || ""}
                          onChange={(event) => onProjectFieldChange("full_script", event.target.value)}
                        />
                      </Field>
                    </div>
                  </PanelCard>

                  <PanelCard eyebrow="Shot Script" title={selectedShot ? `镜头 ${selectedShot.shot_id}` : "当前镜头"}>
                    {selectedShot ? (
                      <div className="form-grid">
                        <Field label="镜头时长（秒）">
                          <input
                            type="number"
                            min="3"
                            max="6"
                            value={selectedShot.shot_duration}
                            onChange={(event) => onShotFieldChange("shot_duration", Number(event.target.value))}
                          />
                        </Field>
                        <Field label="镜头类型">
                          <select value={selectedShot.shot_type} onChange={(event) => onShotFieldChange("shot_type", event.target.value)}>
                            <option value="host">host</option>
                            <option value="explainer">explainer</option>
                            <option value="broll">broll</option>
                            <option value="data">data</option>
                          </select>
                        </Field>
                        <Field label="口播" span>
                          <textarea
                            rows="4"
                            value={selectedShot.narration_text}
                            onChange={(event) => onShotFieldChange("narration_text", event.target.value)}
                          />
                        </Field>
                        <Field label="字幕" span>
                          <textarea
                            rows="3"
                            value={selectedShot.subtitle_text}
                            onChange={(event) => onShotFieldChange("subtitle_text", event.target.value)}
                          />
                        </Field>
                      </div>
                    ) : (
                      <EmptyState title="还没有选中镜头" body="先从中间时间线点一个镜头，再逐段修改口播和字幕。" compact />
                    )}
                  </PanelCard>
                </>
              ) : null}

              {inspectorTab === "visual" ? (
                <>
                  <PanelCard eyebrow="Shot Status" title="当前镜头状态">
                    {selectedShot ? (
                      <div className="context-grid">
                        <div className="context-item">
                          <span>素材状态</span>
                          <strong>{shotStatus.summary}</strong>
                        </div>
                        <div className="context-item">
                          <span>镜头模式</span>
                          <strong>{shotStatus.mode}</strong>
                        </div>
                        <div className="context-item span-2">
                          <span>当前 Provider</span>
                          <strong>{shotStatus.provider}</strong>
                        </div>
                        <div className="context-item span-2">
                          <span>字幕摘要</span>
                          <strong>{selectedShot.subtitle_text || "当前镜头暂无字幕"}</strong>
                        </div>
                      </div>
                    ) : (
                      <EmptyState title="还没有选中镜头" body="先从中间时间线里选一个镜头，再做画面微调。" compact />
                    )}
                  </PanelCard>

                  <PanelCard
                    eyebrow="Step 2"
                    title="画面生成"
                    actions={
                      <>
                        <button type="button" className="ghost-button" disabled={busy || !selectedShot} onClick={onGenerateCurrent}>
                          生成当前镜头
                        </button>
                        <button type="button" className="primary-button" disabled={busy || !project.storyboard.length} onClick={onGenerateAll}>
                          批量生成全部
                        </button>
                      </>
                    }
                  >
                    <ShotPreviewCard projectDetail={projectDetail} selectedShot={selectedShot} />
                    {selectedShot ? (
                      <div className="form-grid">
                        <Field label="中文提示词" span>
                          <textarea
                            rows="5"
                            value={selectedShot.visual_prompt_cn}
                            onChange={(event) => onShotFieldChange("visual_prompt_cn", event.target.value)}
                          />
                        </Field>
                        <Field label="英文提示词" span>
                          <textarea
                            rows="4"
                            value={selectedShot.visual_prompt_en}
                            onChange={(event) => onShotFieldChange("visual_prompt_en", event.target.value)}
                          />
                        </Field>
                        <Field label="镜头运动">
                          <input
                            value={selectedShot.camera_movement}
                            onChange={(event) => onShotFieldChange("camera_movement", event.target.value)}
                          />
                        </Field>
                        <Field label="关键词">
                          <input
                            value={(selectedShot.visual_keywords || []).join("，")}
                            onChange={(event) => onShotFieldChange("visual_keywords", event.target.value)}
                          />
                        </Field>
                        <Field label="安全约束" span>
                          <textarea
                            rows="3"
                            value={selectedShot.safety_notes || ""}
                            onChange={(event) => onShotFieldChange("safety_notes", event.target.value)}
                          />
                        </Field>
                        <label className="checkbox-field span-all">
                          <input
                            type="checkbox"
                            checked={Boolean(selectedShot.needs_real_material)}
                            onChange={(event) => onShotFieldChange("needs_real_material", event.target.checked)}
                          />
                          这个镜头更适合真实素材，不强制走 AI 视频
                        </label>
                      </div>
                    ) : null}
                  </PanelCard>
                </>
              ) : null}

              {inspectorTab === "role" ? (
                <PanelCard
                  eyebrow="Reference"
                  title="角色与参考图"
                  actions={
                    <>
                      <button type="button" className="ghost-button" disabled={busy || !selectedShot} onClick={onGenerateCurrent}>
                        用当前参考图出图
                      </button>
                      <button type="button" className="primary-button" disabled={busy || !project.storyboard.length} onClick={onGenerateAll}>
                        全部镜头重出图
                      </button>
                    </>
                  }
                >
                  <div className="form-grid">
                    <Field label="默认参考图" span note={`不填时自动使用 ${DEFAULT_REFERENCE_HINT}`}>
                      <input
                        value={project.artifacts.resolved_reference_image_path || ""}
                        onChange={(event) => onDefaultReferenceChange(event.target.value)}
                      />
                    </Field>
                    <Field label="当前镜头参考图" span note="留空则沿用默认参考图">
                      <input
                        value={shotReferencePath}
                        disabled={!selectedShot}
                        onChange={(event) => onShotReferenceChange(event.target.value)}
                      />
                    </Field>
                  </div>
                </PanelCard>
              ) : null}

              {inspectorTab === "voice" ? (
                <PanelCard eyebrow="Step 3" title="配音与成片">
                  <div className="form-grid">
                    <Field label="音色">
                      <select
                        value={renderForm.preferred_voice}
                        onChange={(event) => onRenderFieldChange("preferred_voice", event.target.value)}
                      >
                        <option value="professional_cn_male">professional_cn_male</option>
                        <option value="professional_cn_female">professional_cn_female</option>
                        <option value="zh_male_m191_uranus_bigtts">云舟 2.0</option>
                        <option value="zh_female_xiaohe_uranus_bigtts">小何 2.0</option>
                      </select>
                    </Field>
                    <Field label="渲染模式">
                      <select value={renderForm.render_mode} onChange={(event) => onRenderFieldChange("render_mode", event.target.value)}>
                        <option value="video_audio">video_audio</option>
                        <option value="image_audio">image_audio</option>
                      </select>
                    </Field>
                    <Field label="输出画幅">
                      <select value={renderForm.aspect_ratio} onChange={(event) => onRenderFieldChange("aspect_ratio", event.target.value)}>
                        <option value="9:16">9:16 竖屏</option>
                        <option value="16:9">16:9 横屏</option>
                      </select>
                    </Field>
                    <Field label="发布模式">
                      <select value={renderForm.publish_mode} onChange={(event) => onRenderFieldChange("publish_mode", event.target.value)}>
                        <option value="draft">draft</option>
                        <option value="direct">direct</option>
                      </select>
                    </Field>
                    <Field label="最终渲染参考图" span>
                      <input
                        value={renderForm.reference_image_path}
                        onChange={(event) => onRenderFieldChange("reference_image_path", event.target.value)}
                        placeholder="不填则沿用第二步的默认参考图"
                      />
                    </Field>
                    <label className="checkbox-field span-all">
                      <input
                        type="checkbox"
                        checked={renderForm.reuse_existing_shot_images}
                        onChange={(event) => onRenderFieldChange("reuse_existing_shot_images", event.target.checked)}
                      />
                      最终渲染时优先复用第二步已经生成好的镜头图
                    </label>
                  </div>
                  <div className="callout">
                    第三步只负责把镜头图、配音和字幕合成为成片。用户不能逐帧参与视频生成，但可以控制参考图、音色和复用策略。
                  </div>
                  <button type="button" className="primary-button wide" disabled={busy} onClick={onRender}>
                    开始最终合成
                  </button>
                </PanelCard>
              ) : null}

              {inspectorTab === "music" ? (
                <PanelCard eyebrow="Music" title="背景音乐">
                  <div className="callout">
                    这一版先把电网内容的脚本、出图、配音和成片链路做稳，音乐面板先留结构位。后面可以继续接入 BGM 库和混音参数。
                  </div>
                  <div className="music-chip-row">
                    <span className="soft-chip">新闻口播建议：无 BGM</span>
                    <span className="soft-chip">企业宣发建议：轻科技氛围</span>
                    <span className="soft-chip">知识科普建议：低存在感电子垫乐</span>
                  </div>
                </PanelCard>
              ) : null}

              {inspectorTab === "output" ? (
                <>
                  <PanelCard eyebrow="Artifacts" title="产物文件">
                    {artifactEntries.length ? (
                      <div className="artifact-grid">
                        {artifactEntries.map(([label, url]) => (
                          <a key={`${label}-${url}`} href={url} target="_blank" rel="noreferrer" className="artifact-card">
                            <strong>{label}</strong>
                            <span>{url}</span>
                          </a>
                        ))}
                      </div>
                    ) : (
                      <EmptyState title="还没有产物文件" body="完成对应步骤后，这里会显示下载入口。" compact />
                    )}
                  </PanelCard>

                  <PanelCard eyebrow="Media" title="预览与成片">
                    {mediaItems.length ? (
                      <div className="media-grid">
                        {mediaItems.map((item) => (
                          <div key={`${item.title}-${item.url}`} className="media-card">
                            <strong>{item.title}</strong>
                            {item.meta ? <p>{item.meta}</p> : null}
                            {item.kind === "video" ? (
                              <video src={item.url} controls preload="metadata" />
                            ) : (
                              <img src={item.url} alt={item.title} />
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <EmptyState title="还没有可预览素材" body="先去第二步生成镜头图，或者做最终合成。" compact />
                    )}
                  </PanelCard>

                  <PanelCard eyebrow="Attempts" title="接口调用记录">
                    {projectDetail.attempts?.length ? (
                      <div className="attempt-table-wrap">
                        <table className="attempt-table">
                          <thead>
                            <tr>
                              <th>时间</th>
                              <th>Provider</th>
                              <th>动作</th>
                              <th>次数</th>
                              <th>状态</th>
                              <th>错误</th>
                            </tr>
                          </thead>
                          <tbody>
                            {projectDetail.attempts.map((attempt) => {
                              const fallbackProviders = ["mock_video", "mock_image", "static_image_video", "newsroom_preview"];
                              const rowClass =
                                attempt.status === "failed"
                                  ? "failed"
                                  : fallbackProviders.includes(attempt.provider_name)
                                    ? "fallback"
                                    : "";
                              return (
                                <tr key={`${attempt.created_at}-${attempt.provider_name}-${attempt.action_name}-${attempt.attempt_no}`} className={rowClass}>
                                  <td>{attempt.created_at}</td>
                                  <td>{attempt.provider_name}</td>
                                  <td>{attempt.action_name}</td>
                                  <td>{attempt.attempt_no}</td>
                                  <td>
                                    <span className={`status-pill-inline ${attempt.status === "failed" ? "danger" : "ok"}`}>
                                      {attempt.status}
                                    </span>
                                  </td>
                                  <td>{attempt.error_message || "-"}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="还没有接口日志" body="一旦开始出图、配音或合成，这里会直接显示失败原因和回退信息。" compact />
                    )}
                  </PanelCard>
                </>
              ) : null}
            </div>
          </>
        ) : (
          <EmptyState title="先选一个项目" body="右侧会作为 React 版工作流面板使用。现在布局已经改成更紧凑，尽量减少大块留白。" />
        )}
      </section>
    </aside>
  );
}
