const DEFAULT_REFERENCE_HINT = "F:\\AICODING\\需求\\电网人物形象.png";

const state = {
  selectedProjectId: null,
  selectedShotId: null,
  workflowStep: "script",
  inspectorTab: "script",
  previewMode: "shot",
  projectDetail: null,
};

const statusEl = document.getElementById("global-status");
const projectListEl = document.getElementById("project-list");
const projectCountEl = document.getElementById("project-count");
const shotCountChipEl = document.getElementById("shot-count-chip");
const shotListEl = document.getElementById("shot-list");
const projectMetaCompactEl = document.getElementById("project-meta-compact");
const detailTitleEl = document.getElementById("detail-title");
const detailBadgesEl = document.getElementById("detail-badges");
const detailEmptyEl = document.getElementById("detail-empty");
const detailContentEl = document.getElementById("detail-content");
const inspectorEmptyEl = document.getElementById("inspector-empty");
const inspectorContentEl = document.getElementById("inspector-content");
const previewStageEl = document.getElementById("preview-stage");
const previewTitleEl = document.getElementById("preview-title");
const previewSubtitleEl = document.getElementById("preview-subtitle");
const previewProviderChipEl = document.getElementById("preview-provider-chip");
const previewDurationChipEl = document.getElementById("preview-duration-chip");
const diagnosticsPanelEl = document.getElementById("diagnostics-panel");
const timelineStripEl = document.getElementById("timeline-strip");
const artifactLinksEl = document.getElementById("artifact-links");
const mediaGalleryEl = document.getElementById("media-gallery");
const attemptTableEl = document.getElementById("attempt-table");
const automationListEl = document.getElementById("automation-list");
const createDrawerEl = document.getElementById("create-drawer");
const automationDrawerEl = document.getElementById("automation-drawer");
const drawerBackdropEl = document.getElementById("drawer-backdrop");

const saveScriptButton = document.getElementById("save-script-button");
const regenerateStoryboardButton = document.getElementById("regenerate-storyboard-button");
const generateCurrentImageButton = document.getElementById("generate-current-image-button");
const generateAllImagesButton = document.getElementById("generate-all-images-button");
const applyRoleAndGenerateCurrentButton = document.getElementById("apply-role-and-generate-current");
const applyRoleAndGenerateAllButton = document.getElementById("apply-role-and-generate-all");
const runOneClickButton = document.getElementById("run-oneclick-button");
const refreshProjectsButton = document.getElementById("refresh-projects");

const workflowTitleEl = document.getElementById("workflow-title");
const workflowModeEl = document.getElementById("workflow-mode");
const workflowDurationEl = document.getElementById("workflow-duration");
const workflowAspectRatioEl = document.getElementById("workflow-aspect-ratio");
const workflowSummaryEl = document.getElementById("workflow-summary");
const workflowFullScriptEl = document.getElementById("workflow-full-script");
const selectedShotScriptTitleEl = document.getElementById("selected-shot-script-title");
const scriptShotDurationEl = document.getElementById("script-shot-duration");
const scriptShotTypeEl = document.getElementById("script-shot-type");
const scriptShotNarrationEl = document.getElementById("script-shot-narration");
const scriptShotSubtitleEl = document.getElementById("script-shot-subtitle");
const visualPromptCnEl = document.getElementById("visual-prompt-cn");
const visualPromptEnEl = document.getElementById("visual-prompt-en");
const visualCameraEl = document.getElementById("visual-camera");
const visualKeywordsEl = document.getElementById("visual-keywords");
const visualSafetyEl = document.getElementById("visual-safety");
const visualRealMaterialEl = document.getElementById("visual-real-material");
const visualShotPreviewEl = document.getElementById("visual-shot-preview");
const defaultReferenceInputEl = document.getElementById("default-reference-image");
const selectedShotReferenceEl = document.getElementById("selected-shot-reference");
const renderFormEl = document.getElementById("form-render");

document.querySelectorAll(".drawer-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".drawer-tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".source-pane").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.sourcePane).classList.add("active");
  });
});

document.querySelectorAll(".inspector-tab").forEach((button) => {
  button.addEventListener("click", () => switchInspectorTab(button.dataset.inspectorTab));
});

document.querySelectorAll(".workflow-step-button").forEach((button) => {
  button.addEventListener("click", () => switchWorkflowStep(button.dataset.workflowStep));
});

document.querySelectorAll(".preview-mode-button").forEach((button) => {
  button.addEventListener("click", () => switchPreviewMode(button.dataset.previewMode));
});

document.getElementById("open-create-drawer").addEventListener("click", () => openDrawer("create"));
document.getElementById("open-automation-drawer").addEventListener("click", () => openDrawer("automation"));
document.querySelectorAll("[data-close-drawer]").forEach((button) => {
  button.addEventListener("click", () => closeDrawers());
});
drawerBackdropEl.addEventListener("click", () => closeDrawers());

refreshProjectsButton.addEventListener("click", () => loadProjects(state.selectedProjectId));
runOneClickButton.addEventListener("click", () => runOneClickWorkflow());
saveScriptButton.addEventListener("click", () => saveWorkflowScript(false));
regenerateStoryboardButton.addEventListener("click", () => saveWorkflowScript(true));
generateCurrentImageButton.addEventListener("click", () => generateWorkflowImages(getSelectedShot() ? [getSelectedShot().shot_id] : []));
generateAllImagesButton.addEventListener("click", () => generateWorkflowImages());
applyRoleAndGenerateCurrentButton.addEventListener("click", () => generateWorkflowImages(getSelectedShot() ? [getSelectedShot().shot_id] : []));
applyRoleAndGenerateAllButton.addEventListener("click", () => generateWorkflowImages());

renderFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  await renderWorkflowProject();
});

bindCreateForm("form-create-text", "/projects/create_from_text", { target_duration_seconds: "number" });
bindCreateForm("form-create-script", "/projects/create_from_script", { target_duration_seconds: "number" });
bindCreateForm("form-create-url", "/projects/create_from_url", { target_duration_seconds: "number" });
bindCreateForm("form-create-feed", "/projects/create_from_rpa_feed", {
  target_duration_seconds: "number",
  render_preview_bundle: "checkbox",
});
bindAutomationForm();

async function bindCreateForm(formId, endpoint, typeMap) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setBusy(true, "正在创建项目草稿...");
    try {
      const payload = formToJSON(form, typeMap);
      const response = await fetchJSON(endpoint, { method: "POST", body: JSON.stringify(payload) });
      form.reset();
      if (formId === "form-create-feed") form.querySelector("[name='render_preview_bundle']").checked = true;
      closeDrawers();
      setStatus(`项目 ${response.project_id} 已创建`, "success");
      await loadProjects(response.project_id);
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      setBusy(false);
    }
  });
}

function bindAutomationForm() {
  const form = document.getElementById("form-create-automation");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setBusy(true, "正在创建自动任务...");
    try {
      const payload = formToJSON(form, {
        interval_minutes: "number",
        target_duration_seconds: "number",
        per_source_limit: "number",
        total_fetch_limit: "number",
        auto_render: "checkbox",
        reference_image_path: "nullable-string",
      });
      await fetchJSON("/automation/jobs", { method: "POST", body: JSON.stringify(payload) });
      form.reset();
      form.querySelector("[name='auto_render']").checked = true;
      setStatus("自动任务已创建", "success");
      await loadAutomationJobs();
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      setBusy(false);
    }
  });
}

function openDrawer(name) {
  closeDrawers();
  drawerBackdropEl.classList.remove("hidden");
  if (name === "create") createDrawerEl.classList.remove("hidden");
  if (name === "automation") automationDrawerEl.classList.remove("hidden");
}

function closeDrawers() {
  drawerBackdropEl.classList.add("hidden");
  createDrawerEl.classList.add("hidden");
  automationDrawerEl.classList.add("hidden");
}

function setBusy(isBusy, message = "") {
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy;
  });
  if (message) setStatus(message, "info");
}

function setStatus(message, tone = "info") {
  statusEl.textContent = message;
  statusEl.className = `status-pill ${tone}`;
}

function formToJSON(form, typeMap = {}) {
  const payload = {};
  const formData = new FormData(form);
  for (const [key, rawValue] of formData.entries()) {
    const strategy = typeMap[key];
    if (strategy === "number") payload[key] = Number(rawValue);
    else if (strategy === "nullable-string") payload[key] = String(rawValue || "").trim() || null;
    else payload[key] = typeof rawValue === "string" ? rawValue.trim() : rawValue;
  }
  for (const [key, strategy] of Object.entries(typeMap)) {
    if (strategy === "checkbox") {
      const field = form.querySelector(`[name="${key}"]`);
      payload[key] = Boolean(field && field.checked);
    }
  }
  return payload;
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) throw new Error(data?.detail || `Request failed with status ${response.status}`);
  return data;
}

async function loadProjects(preferredProjectId = null) {
  const items = await fetchJSON("/projects?limit=50");
  renderProjectList(items);
  const targetId = preferredProjectId || state.selectedProjectId || items[0]?.project_id || null;
  if (!targetId) {
    renderEmptyWorkspace();
    return;
  }
  await loadProject(targetId);
}

async function loadProject(projectId) {
  const detail = await fetchJSON(`/projects/${projectId}`);
  applyLoadedDetail(detail, state.selectedShotId);
  renderWorkspace();
}

function applyLoadedDetail(detail, preferredShotId = null) {
  state.projectDetail = deepClone(detail);
  state.selectedProjectId = detail.project.project_id;
  const shotIds = detail.project.storyboard.map((shot) => shot.shot_id);
  state.selectedShotId = shotIds.includes(preferredShotId) ? preferredShotId : shotIds[0] || null;
}

function renderProjectList(items) {
  projectCountEl.textContent = String(items.length);
  if (!items.length) {
    projectListEl.innerHTML = `<div class="project-card"><strong>还没有项目</strong><div class="project-meta-compact">点右上角“新建项目”就能开始。</div></div>`;
    return;
  }
  projectListEl.innerHTML = items.map((item) => `
    <button class="project-card ${item.project_id === state.selectedProjectId ? "active" : ""}" type="button" data-project-id="${item.project_id}">
      <strong>${escapeHTML(item.title)}</strong>
      <div>${escapeHTML(item.project_id)}</div>
      <div class="project-meta-row">
        <span class="mini-chip">${escapeHTML(item.status)}</span>
        <span class="mini-chip">${escapeHTML(item.mode)}</span>
        <span class="mini-chip">${escapeHTML(item.source_type)}</span>
        <span class="mini-chip">${escapeHTML(String(item.shot_count))} 镜头</span>
      </div>
    </button>
  `).join("");
  projectListEl.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      syncInspectorToState();
      await loadProject(button.dataset.projectId);
    });
  });
}

function renderWorkspace() {
  if (!state.projectDetail) {
    renderEmptyWorkspace();
    return;
  }
  const { project, attempts } = state.projectDetail;
  detailEmptyEl.classList.add("hidden");
  detailContentEl.classList.remove("hidden");
  inspectorEmptyEl.classList.add("hidden");
  inspectorContentEl.classList.remove("hidden");

  detailTitleEl.textContent = project.summary?.title || project.content_input.title || project.project_id;
  detailBadgesEl.innerHTML = [
    badge(project.status, project.status === "failed"),
    badge(project.content_input.mode),
    badge(project.content_input.aspect_ratio),
    badge(project.content_input.source_type),
    badge(`${project.storyboard.length} 镜头`),
  ].join("");

  shotCountChipEl.textContent = String(project.storyboard.length);
  projectMetaCompactEl.innerHTML = `
    <strong>${escapeHTML(project.summary?.title || project.content_input.title || project.project_id)}</strong>
    <div>状态：${escapeHTML(project.status)}</div>
    <div>模式：${escapeHTML(project.content_input.mode)}，画幅：${escapeHTML(project.content_input.aspect_ratio)}</div>
    <div>默认参考图：${escapeHTML(project.artifacts.resolved_reference_image_path || DEFAULT_REFERENCE_HINT)}</div>
  `;

  renderWorkflowRibbon(project);
  renderShotCollections();
  renderPreview();
  renderDiagnostics(project, attempts);
  renderInspectorForms();
  renderOutput();
}

function renderEmptyWorkspace() {
  state.projectDetail = null;
  state.selectedShotId = null;
  detailTitleEl.textContent = "请选择左侧项目";
  detailBadgesEl.innerHTML = "";
  detailContentEl.classList.add("hidden");
  detailEmptyEl.classList.remove("hidden");
  inspectorContentEl.classList.add("hidden");
  inspectorEmptyEl.classList.remove("hidden");
  shotCountChipEl.textContent = "0";
  shotListEl.innerHTML = `<div class="shot-card"><div class="shot-text"><strong>暂无镜头</strong><p>选中项目后，这里会显示逐镜头列表。</p></div></div>`;
  timelineStripEl.innerHTML = "";
}

function renderWorkflowRibbon(project) {
  const labels = {
    script: `1. 文案与分镜 · ${project.storyboard.length} 镜头`,
    images: `2. 镜头图片 · ${project.artifacts.shot_images.length}/${project.storyboard.length}`,
    render: `3. 最终成片 · ${project.artifacts.composition ? "已输出" : "待合成"}`,
  };
  document.querySelectorAll(".workflow-step-button").forEach((button) => {
    button.textContent = labels[button.dataset.workflowStep];
    button.classList.toggle("active", button.dataset.workflowStep === state.workflowStep);
  });
}

function renderShotCollections() {
  const project = state.projectDetail.project;
  shotListEl.innerHTML = project.storyboard.map((shot) => {
    const excerpt = truncate(shot.narration_text || shot.subtitle_text || "暂无文案", 58);
    const imageReady = Boolean(findShotImage(shot.shot_id));
    const videoReady = Boolean(findShotVideo(shot.shot_id));
    return `
      <button class="shot-card ${shot.shot_id === state.selectedShotId ? "active" : ""}" type="button" data-shot-id="${shot.shot_id}">
        ${getShotThumbHTML(shot.shot_id, "shot-thumb")}
        <div class="shot-text">
          <strong class="shot-card-title">镜头 ${shot.shot_id}</strong>
          <p>${escapeHTML(excerpt)}</p>
          <div class="shot-meta-row">
            <span class="mini-chip">${escapeHTML(String(shot.shot_duration))} 秒</span>
            <span class="mini-chip">${escapeHTML(shot.shot_type)}</span>
            <span class="mini-chip">${imageReady ? "已出图" : "待出图"}</span>
            <span class="mini-chip">${videoReady ? "已有视频" : "静态预览"}</span>
          </div>
        </div>
      </button>
    `;
  }).join("") || `<div class="shot-card"><div class="shot-text"><strong>暂无镜头</strong><p>当前项目还没有拆分出分镜。</p></div></div>`;

  timelineStripEl.innerHTML = project.storyboard.map((shot) => `
    <button class="timeline-card ${shot.shot_id === state.selectedShotId ? "active" : ""}" type="button" data-timeline-shot-id="${shot.shot_id}">
      ${getShotThumbHTML(shot.shot_id, "timeline-thumb")}
      <strong class="timeline-card-title">镜头 ${shot.shot_id}</strong>
      <div class="timeline-meta-row">
        <span class="mini-chip">${escapeHTML(String(shot.shot_duration))} 秒</span>
        <span class="mini-chip">${escapeHTML(shot.shot_type)}</span>
      </div>
    </button>
  `).join("");

  shotListEl.querySelectorAll("[data-shot-id]").forEach((button) => {
    button.addEventListener("click", () => {
      syncInspectorToState();
      state.selectedShotId = Number(button.dataset.shotId);
      renderShotCollections();
      renderPreview();
      renderInspectorForms();
    });
  });
  timelineStripEl.querySelectorAll("[data-timeline-shot-id]").forEach((button) => {
    button.addEventListener("click", () => {
      syncInspectorToState();
      state.selectedShotId = Number(button.dataset.timelineShotId);
      renderShotCollections();
      renderPreview();
      renderInspectorForms();
    });
  });
}

function renderPreview() {
  if (!state.projectDetail) return;
  const project = state.projectDetail.project;
  const shot = getSelectedShot();
  const aspectRatio = shot?.aspect_ratio || project.content_input.aspect_ratio || "16:9";
  previewStageEl.className = `preview-stage ${aspectRatio === "9:16" ? "aspect-9-16" : "aspect-16-9"}`;

  let html = "";
  let title = "当前还没有可预览内容";
  let subtitle = "完成文案拆分或镜头生成后，这里会显示实时预览。";
  let provider = "等待素材";
  let duration = "--";

  if (state.previewMode === "final") {
    const finalUrl = state.projectDetail.asset_links.final_video_url;
    if (finalUrl) {
      title = "最终成片";
      subtitle = "这里显示最终输出的视频成片。";
      provider = project.artifacts.composition?.provider_name || "final_video";
      duration = formatDuration(sumShotDuration(project.storyboard));
      html = `<div class="preview-media-shell"><video src="${finalUrl}" controls preload="metadata"></video></div>`;
    }
  } else if (state.previewMode === "preview") {
    const previewUrl = state.projectDetail.asset_links.preview_video_url || state.projectDetail.asset_links.preview_gif_url || state.projectDetail.asset_links.preview_cover_url;
    if (previewUrl) {
      title = "RPA 预览";
      subtitle = "这里显示 newsroom 预览包产物。";
      provider = "newsroom_preview";
      duration = formatDuration(sumShotDuration(project.storyboard));
      html = previewUrl.endsWith(".mp4")
        ? `<div class="preview-media-shell"><video src="${previewUrl}" controls preload="metadata"></video></div>`
        : `<div class="preview-media-shell"><img src="${previewUrl}" alt="RPA preview" /></div>`;
    }
  } else if (shot) {
    const shotVideo = findShotVideo(shot.shot_id);
    const shotImage = findShotImage(shot.shot_id);
    title = `镜头 ${shot.shot_id}`;
    subtitle = shot.narration_text || shot.subtitle_text || "当前镜头暂无文案。";
    duration = formatDuration(shot.shot_duration);
    if (shotVideo) {
      provider = `${shotVideo.provider_name}${shotVideo.used_fallback ? " / fallback" : ""}`;
      html = `<div class="preview-media-shell"><video src="${normalizeRuntimeUrl(shotVideo.video_path)}" controls preload="metadata"></video></div>`;
    } else if (shotImage) {
      provider = `${shotImage.provider_name}${shotImage.used_fallback ? " / fallback" : ""}`;
      html = `<div class="preview-media-shell"><img src="${normalizeRuntimeUrl(shotImage.image_path)}" alt="shot-${shot.shot_id}" /></div>`;
    }
  }

  if (!html) {
    html = `<div class="preview-placeholder">当前模式下还没有可展示素材。你可以先去右侧“画面”面板出图，或者切换到其他预览模式。</div>`;
  }

  previewStageEl.innerHTML = html;
  previewTitleEl.textContent = title;
  previewSubtitleEl.textContent = subtitle;
  previewProviderChipEl.textContent = provider;
  previewDurationChipEl.textContent = duration;

  document.querySelectorAll(".preview-mode-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.previewMode === state.previewMode);
  });
}

function renderDiagnostics(project, attempts) {
  const failedAttempts = attempts.filter((item) => item.status === "failed");
  const failedVideoAttempts = failedAttempts.filter((item) => item.action_name.includes("generate_video"));
  const fallbackVideos = (project.artifacts.shot_videos || []).filter((item) => item.used_fallback || ["mock_video", "static_image_video"].includes(item.provider_name));
  const fallbackImages = (project.artifacts.shot_images || []).filter((item) => item.used_fallback || ["mock_image", "newsroom_preview"].includes(item.provider_name));
  const latestError = [...failedAttempts].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))[0];

  const cards = [
    diagnosticCard(
      "项目状态",
      project.status === "failed" ? "danger" : project.status === "rendered" ? "success" : "warning",
      project.status === "failed" ? "项目存在失败步骤" : project.status === "rendered" ? "项目已完成成片输出" : "项目还在草稿或处理中",
      project.status === "rendering"
        ? "终端里大量 304 / 206 一般只是浏览器正在读缓存或播放视频，不代表后台还在生成。"
        : "状态会随着文案、图片和成片步骤推进实时更新。"
    ),
    diagnosticCard(
      "参考图",
      project.artifacts.resolved_reference_image_path ? "success" : "warning",
      project.artifacts.resolved_reference_image_path ? "当前项目已锁定默认参考图" : "当前项目未手动指定参考图",
      project.artifacts.resolved_reference_image_path || `系统会自动回退到默认人物图：${DEFAULT_REFERENCE_HINT}`
    ),
    diagnosticCard(
      "镜头图片",
      fallbackImages.length ? "warning" : "success",
      `${project.artifacts.shot_images.length}/${project.storyboard.length} 个镜头已有图片`,
      fallbackImages.length
        ? `其中 ${fallbackImages.length} 个镜头用了 fallback 图像：${summarizeProviders(fallbackImages.map((item) => item.provider_name))}`
        : "镜头图已经满足最终合成前置条件。"
    ),
    diagnosticCard(
      "视频生成",
      failedVideoAttempts.length || fallbackVideos.length ? "warning" : "success",
      failedVideoAttempts.length ? `真实视频接口失败 ${failedVideoAttempts.length} 次` : "当前没有视频接口失败记录",
      fallbackVideos.length
        ? `有 ${fallbackVideos.length} 个镜头自动回退成静态图视频，所以你会看到“有字幕但画面不动”的情况。`
        : "当前镜头视频状态正常。"
    ),
  ];
  if (latestError) cards.push(diagnosticCard("最近错误", "danger", `${latestError.provider_name} / ${latestError.action_name}`, latestError.error_message || "没有更详细的错误信息"));
  diagnosticsPanelEl.innerHTML = cards.join("");
}

function renderInspectorForms() {
  if (!state.projectDetail) return;
  const project = state.projectDetail.project;
  const shot = getSelectedShot();
  const shotReferencePaths = project.artifacts.shot_reference_paths || {};

  workflowTitleEl.value = project.summary?.title || project.content_input.title || "";
  workflowModeEl.value = project.content_input.mode;
  workflowDurationEl.value = project.content_input.target_duration_seconds;
  workflowAspectRatioEl.value = project.content_input.aspect_ratio;
  workflowSummaryEl.value = project.summary?.summary || "";
  workflowFullScriptEl.value = project.script?.full_script || project.content_input.raw_text || "";

  selectedShotScriptTitleEl.textContent = shot ? `镜头 ${shot.shot_id}` : "当前镜头";
  scriptShotDurationEl.value = shot ? shot.shot_duration : "";
  scriptShotTypeEl.value = shot ? shot.shot_type : "host";
  scriptShotNarrationEl.value = shot ? shot.narration_text : "";
  scriptShotSubtitleEl.value = shot ? shot.subtitle_text : "";
  visualPromptCnEl.value = shot ? shot.visual_prompt_cn : "";
  visualPromptEnEl.value = shot ? shot.visual_prompt_en : "";
  visualCameraEl.value = shot ? shot.camera_movement : "";
  visualKeywordsEl.value = shot ? (shot.visual_keywords || []).join("，") : "";
  visualSafetyEl.value = shot ? shot.safety_notes || "" : "";
  visualRealMaterialEl.checked = Boolean(shot?.needs_real_material);
  defaultReferenceInputEl.value = project.artifacts.resolved_reference_image_path || "";
  selectedShotReferenceEl.value = shot ? shotReferencePaths[String(shot.shot_id)] || "" : "";

  renderFormEl.querySelector("[name='render_mode']").value = project.artifacts.last_render_mode || renderFormEl.querySelector("[name='render_mode']").value || "image_audio";
  renderFormEl.querySelector("[name='aspect_ratio']").value = project.content_input.aspect_ratio;
  renderFormEl.querySelector("[name='reference_image_path']").value = project.artifacts.resolved_reference_image_path || "";
  renderFormEl.querySelector("[name='reuse_existing_shot_images']").checked = true;

  renderVisualShotPreview(shot);
  switchInspectorTab(state.inspectorTab);
}

function renderVisualShotPreview(shot) {
  if (!shot) {
    visualShotPreviewEl.className = "shot-preview-card placeholder";
    visualShotPreviewEl.innerHTML = "当前项目还没有镜头。";
    return;
  }
  const shotVideo = findShotVideo(shot.shot_id);
  const shotImage = findShotImage(shot.shot_id);
  const mediaUrl = shotVideo
    ? normalizeRuntimeUrl(shotVideo.poster_path || shotVideo.video_path)
    : shotImage
      ? normalizeRuntimeUrl(shotImage.image_path)
      : "";
  const provider = shotVideo
    ? `${shotVideo.provider_name}${shotVideo.used_fallback ? " / fallback" : ""}`
    : shotImage
      ? `${shotImage.provider_name}${shotImage.used_fallback ? " / fallback" : ""}`
      : "还没有素材";
  if (!mediaUrl) {
    visualShotPreviewEl.className = "shot-preview-card placeholder";
    visualShotPreviewEl.innerHTML = `镜头 ${shot.shot_id} 还没有图像素材。`;
    return;
  }
  visualShotPreviewEl.className = "shot-preview-card";
  visualShotPreviewEl.innerHTML = `
    <strong>镜头 ${shot.shot_id} 预览</strong>
    <div class="helper-text">Provider：${escapeHTML(provider)}</div>
    <img src="${mediaUrl}" alt="shot-${shot.shot_id}" loading="lazy" />
  `;
}

function renderOutput() {
  if (!state.projectDetail) return;
  const { project, asset_links: assetLinks, attempts } = state.projectDetail;
  artifactLinksEl.innerHTML = renderArtifactLinks(project, assetLinks);
  mediaGalleryEl.innerHTML = renderMediaGallery(project, assetLinks);
  attemptTableEl.innerHTML = renderAttempts(attempts);
}

function renderArtifactLinks(project, assetLinks) {
  const entries = [
    ["summary.json", normalizeRuntimeUrl(project.artifacts.summary_path)],
    ["script.json", normalizeRuntimeUrl(project.artifacts.script_path)],
    ["storyboard.json", normalizeRuntimeUrl(project.artifacts.storyboard_path)],
    ["news_plan.json", normalizeRuntimeUrl(project.artifacts.news_plan_path)],
    ["run_report.json", normalizeRuntimeUrl(project.artifacts.news_report_path)],
    ["selected_sources.md", normalizeRuntimeUrl(project.artifacts.selected_sources_path)],
    ["音频", assetLinks.audio_url],
    ["字幕", assetLinks.subtitle_url],
    ["发布包", assetLinks.publish_payload_url],
  ].filter((item) => item[1]);
  if (!entries.length) {
    return `<div class="link-card"><strong>当前还没有产物文件</strong><div class="helper-text">完成对应步骤后，这里会提供可下载路径。</div></div>`;
  }
  return entries.map(([label, url]) => `
    <div class="link-card">
      <strong>${escapeHTML(label)}</strong>
      <a href="${url}" target="_blank" rel="noreferrer">${escapeHTML(url)}</a>
    </div>
  `).join("");
}

function renderMediaGallery(project, assetLinks) {
  const cards = [];
  if (assetLinks.final_video_url) cards.push(mediaVideo("最终成片", assetLinks.final_video_url));
  if (assetLinks.preview_video_url) cards.push(mediaVideo("RPA 预览 MP4", assetLinks.preview_video_url));
  if (assetLinks.preview_gif_url) cards.push(mediaImage("RPA 预览 GIF", assetLinks.preview_gif_url));
  if (assetLinks.preview_cover_url) cards.push(mediaImage("RPA 封面", assetLinks.preview_cover_url));
  (project.artifacts.shot_images || []).slice(0, 8).forEach((item) => {
    const url = normalizeRuntimeUrl(item.image_path);
    if (url) cards.push(mediaImage(`镜头图 ${item.shot_id}`, url, `${item.provider_name}${item.used_fallback ? " / fallback" : ""}`));
  });
  (project.artifacts.shot_videos || []).slice(0, 6).forEach((item) => {
    const url = normalizeRuntimeUrl(item.video_path);
    if (url) cards.push(mediaVideo(`镜头视频 ${item.shot_id}`, url, `${item.provider_name}${item.used_fallback ? " / fallback" : ""}`));
  });
  return cards.length
    ? cards.join("")
    : `<div class="media-card"><strong>还没有可预览素材</strong><div class="helper-text">可以先去“画面”面板生成镜头图。</div></div>`;
}

function renderAttempts(attempts) {
  if (!attempts.length) {
    return `<div class="link-card"><strong>当前还没有接口调用记录</strong><div class="helper-text">开始出图、配音或合成后，这里会显示详细日志。</div></div>`;
  }
  const fallbackProviders = ["mock_video", "mock_image", "static_image_video", "newsroom_preview"];
  const rows = attempts.map((item) => {
    const rowClass = item.status === "failed" ? "failed-row" : fallbackProviders.includes(item.provider_name) ? "fallback-row" : "";
    const statusClass = item.status === "failed" ? "failed" : "success";
    return `
      <tr class="${rowClass}">
        <td>${escapeHTML(item.created_at)}</td>
        <td>${escapeHTML(item.provider_name)}</td>
        <td>${escapeHTML(item.action_name)}</td>
        <td>${escapeHTML(String(item.attempt_no))}</td>
        <td><span class="attempt-status ${statusClass}">${escapeHTML(item.status)}</span></td>
        <td>${escapeHTML(item.error_message || "-")}</td>
      </tr>
    `;
  }).join("");
  return `
    <table class="attempt-table">
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
      <tbody>${rows}</tbody>
    </table>
  `;
}

function syncInspectorToState() {
  if (!state.projectDetail) return;
  const project = state.projectDetail.project;
  const shot = getSelectedShot();
  const title = workflowTitleEl.value.trim();
  if (project.summary) project.summary.title = title;
  if (project.script) project.script.title = title;
  project.content_input.title = title;
  project.content_input.mode = workflowModeEl.value;
  project.content_input.target_duration_seconds = Number(workflowDurationEl.value || 60);
  project.content_input.aspect_ratio = workflowAspectRatioEl.value;
  if (project.summary) project.summary.summary = workflowSummaryEl.value.trim();
  if (project.script) project.script.full_script = workflowFullScriptEl.value.trim();
  project.content_input.raw_text = workflowFullScriptEl.value.trim();
  project.artifacts.resolved_reference_image_path = defaultReferenceInputEl.value.trim();
  if (!shot) return;
  shot.shot_duration = Number(scriptShotDurationEl.value || shot.shot_duration || 4);
  shot.shot_type = scriptShotTypeEl.value;
  shot.narration_text = scriptShotNarrationEl.value.trim();
  shot.subtitle_text = scriptShotSubtitleEl.value.trim();
  shot.visual_prompt_cn = visualPromptCnEl.value.trim();
  shot.visual_prompt_en = visualPromptEnEl.value.trim();
  shot.camera_movement = visualCameraEl.value.trim();
  shot.visual_keywords = visualKeywordsEl.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean);
  shot.safety_notes = visualSafetyEl.value.trim();
  shot.needs_real_material = visualRealMaterialEl.checked;
  shot.aspect_ratio = workflowAspectRatioEl.value;
  if (!project.artifacts.shot_reference_paths) project.artifacts.shot_reference_paths = {};
  const shotReference = selectedShotReferenceEl.value.trim();
  if (shotReference) project.artifacts.shot_reference_paths[String(shot.shot_id)] = shotReference;
  else delete project.artifacts.shot_reference_paths[String(shot.shot_id)];
}

function collectScriptPayload(regenerateStoryboard = false) {
  syncInspectorToState();
  const project = state.projectDetail.project;
  return {
    title: project.summary?.title || project.content_input.title || "",
    full_script: project.script?.full_script || project.content_input.raw_text || "",
    summary: project.summary?.summary || "",
    mode: project.content_input.mode,
    target_duration_seconds: project.content_input.target_duration_seconds,
    aspect_ratio: project.content_input.aspect_ratio,
    regenerate_storyboard: regenerateStoryboard,
    storyboard: regenerateStoryboard ? [] : project.storyboard,
  };
}

function collectImagePayload(shotIds = []) {
  syncInspectorToState();
  const project = state.projectDetail.project;
  return {
    aspect_ratio: project.content_input.aspect_ratio,
    render_mode: renderFormEl.querySelector("[name='render_mode']").value,
    reference_image_path: defaultReferenceInputEl.value.trim() || null,
    shot_reference_overrides: project.artifacts.shot_reference_paths || {},
    shot_ids: shotIds,
  };
}

function collectRenderPayload() {
  syncInspectorToState();
  return {
    preferred_voice: renderFormEl.querySelector("[name='preferred_voice']").value,
    publish_mode: renderFormEl.querySelector("[name='publish_mode']").value,
    render_mode: renderFormEl.querySelector("[name='render_mode']").value,
    aspect_ratio: renderFormEl.querySelector("[name='aspect_ratio']").value,
    reference_image_path: renderFormEl.querySelector("[name='reference_image_path']").value.trim() || null,
    reuse_existing_shot_images: renderFormEl.querySelector("[name='reuse_existing_shot_images']").checked,
  };
}

async function saveWorkflowScript(regenerateStoryboard) {
  if (!state.selectedProjectId) return setStatus("请先选择一个项目。", "error");
  setBusy(true, regenerateStoryboard ? "正在重新拆分分镜..." : "正在保存文案与分镜...");
  try {
    const detail = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/script`, {
      method: "PUT",
      body: JSON.stringify(collectScriptPayload(regenerateStoryboard)),
    });
    applyLoadedDetail(detail, regenerateStoryboard ? null : state.selectedShotId);
    renderWorkspace();
    switchWorkflowStep("script");
    setStatus(regenerateStoryboard ? "分镜已重新生成。" : "文案与分镜已保存。", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function generateWorkflowImages(shotIds = []) {
  if (!state.selectedProjectId) return setStatus("请先选择一个项目。", "error");
  if (!state.projectDetail.project.storyboard.length) return setStatus("当前项目还没有可出图的镜头。", "error");
  setBusy(true, shotIds.length ? `正在生成镜头 ${shotIds.join(", ")} 的图片...` : "正在批量生成镜头图片...");
  try {
    const detail = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/images`, {
      method: "POST",
      body: JSON.stringify(collectImagePayload(shotIds)),
    });
    applyLoadedDetail(detail, state.selectedShotId);
    renderWorkspace();
    switchWorkflowStep("images");
    setStatus(shotIds.length ? "当前镜头图片已更新。" : "镜头图片已批量生成。", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function renderWorkflowProject() {
  if (!state.selectedProjectId) return setStatus("请先选择一个项目。", "error");
  setBusy(true, "正在进行最终合成...");
  try {
    const response = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/render`, {
      method: "POST",
      body: JSON.stringify(collectRenderPayload()),
    });
    setStatus(`最终成片已输出，本次累计 Provider 尝试 ${response.attempt_count} 次。`, "success");
    await loadProject(state.selectedProjectId);
    switchWorkflowStep("render");
    switchPreviewMode("final");
    switchInspectorTab("output");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function runOneClickWorkflow() {
  if (!state.selectedProjectId) return setStatus("请先选择一个项目。", "error");
  setBusy(true, "正在一键执行完整流程...");
  try {
    const step1 = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/script`, {
      method: "PUT",
      body: JSON.stringify(collectScriptPayload(false)),
    });
    applyLoadedDetail(step1, state.selectedShotId);
    const step2 = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/images`, {
      method: "POST",
      body: JSON.stringify(collectImagePayload()),
    });
    applyLoadedDetail(step2, state.selectedShotId);
    const response = await fetchJSON(`/projects/${state.selectedProjectId}/workflow/render`, {
      method: "POST",
      body: JSON.stringify(collectRenderPayload()),
    });
    setStatus(`一键成片完成，累计 Provider 尝试 ${response.attempt_count} 次。`, "success");
    await loadProject(state.selectedProjectId);
    switchWorkflowStep("render");
    switchPreviewMode("final");
    switchInspectorTab("output");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function loadAutomationJobs() {
  const jobs = await fetchJSON("/automation/jobs?limit=100");
  if (!jobs.length) {
    automationListEl.innerHTML = `<div class="automation-card"><strong>还没有自动任务</strong><div class="automation-meta">创建后就能自动抓站点、自动建项目、自动渲染。</div></div>`;
    return;
  }
  automationListEl.innerHTML = jobs.map((job) => `
    <article class="automation-card">
      <strong>${escapeHTML(job.name)}</strong>
      <div class="automation-meta">
        <div>${escapeHTML(job.job_id)} · ${escapeHTML(job.status)}</div>
        <div>${escapeHTML(job.fetch.source_set)} · 每 ${escapeHTML(String(job.interval_minutes))} 分钟</div>
        <div>最近运行：${escapeHTML(job.last_run_at ? new Date(job.last_run_at).toLocaleString() : "从未运行")}</div>
        <div>下次运行：${escapeHTML(job.next_run_at ? new Date(job.next_run_at).toLocaleString() : "未安排")}</div>
        ${job.last_error ? `<div>错误：${escapeHTML(job.last_error)}</div>` : ""}
      </div>
      <div class="inline-actions">
        <button class="action-button" type="button" data-automation-run="${job.job_id}">立即运行</button>
        <button class="action-button" type="button" data-automation-toggle="${job.job_id}" data-next-status="${job.status === "paused" ? "active" : "paused"}">${job.status === "paused" ? "恢复" : "暂停"}</button>
      </div>
    </article>
  `).join("");
  automationListEl.querySelectorAll("[data-automation-run]").forEach((button) => {
    button.addEventListener("click", () => runAutomation(button.dataset.automationRun));
  });
  automationListEl.querySelectorAll("[data-automation-toggle]").forEach((button) => {
    button.addEventListener("click", () => toggleAutomation(button.dataset.automationToggle, button.dataset.nextStatus));
  });
}

async function runAutomation(jobId) {
  setBusy(true, "自动任务执行中...");
  try {
    const run = await fetchJSON(`/automation/jobs/${jobId}/run`, { method: "POST" });
    setStatus(`自动任务执行完成：${run.status}`, "success");
    if (run.project_id) await loadProjects(run.project_id);
    else await loadAutomationJobs();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function toggleAutomation(jobId, nextStatus) {
  setBusy(true, "正在更新任务状态...");
  try {
    await fetchJSON(`/automation/jobs/${jobId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: nextStatus }),
    });
    setStatus("自动任务状态已更新。", "success");
    await loadAutomationJobs();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function switchWorkflowStep(step) {
  state.workflowStep = step;
  const tabMap = { script: "script", images: "visual", render: "voice" };
  document.querySelectorAll(".workflow-step-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.workflowStep === step);
  });
  switchInspectorTab(tabMap[step] || "script");
}

function switchInspectorTab(tab) {
  state.inspectorTab = tab;
  document.querySelectorAll(".inspector-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.inspectorTab === tab);
  });
  document.querySelectorAll(".inspector-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `inspector-pane-${tab}`);
  });
}

function switchPreviewMode(mode) {
  state.previewMode = mode;
  renderPreview();
}

function getSelectedShot() {
  return state.projectDetail?.project.storyboard.find((shot) => shot.shot_id === state.selectedShotId) || null;
}

function findShotImage(shotId) {
  return state.projectDetail?.project.artifacts.shot_images.find((item) => item.shot_id === shotId) || null;
}

function findShotVideo(shotId) {
  return state.projectDetail?.project.artifacts.shot_videos.find((item) => item.shot_id === shotId) || null;
}

function getShotThumbHTML(shotId, className) {
  const shotVideo = findShotVideo(shotId);
  const shotImage = findShotImage(shotId);
  const url = shotVideo
    ? normalizeRuntimeUrl(shotVideo.poster_path || shotVideo.video_path)
    : shotImage
      ? normalizeRuntimeUrl(shotImage.image_path)
      : "";
  return url
    ? `<img class="${className}" src="${url}" alt="shot-${shotId}" loading="lazy" />`
    : `<div class="${className} placeholder">暂无画面</div>`;
}

function sumShotDuration(shots) {
  return shots.reduce((sum, shot) => sum + Number(shot.shot_duration || 0), 0);
}

function formatDuration(seconds) {
  if (!Number.isFinite(Number(seconds))) return "--";
  const total = Math.max(0, Math.round(Number(seconds)));
  const minutes = Math.floor(total / 60);
  const remainder = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function badge(text, failed = false) {
  return `<span class="badge ${failed ? "badge-failed" : ""}">${escapeHTML(text)}</span>`;
}

function diagnosticCard(label, tone, headline, body) {
  return `
    <article class="diagnostic-card ${tone}">
      <div class="mini-chip">${escapeHTML(label)}</div>
      <strong>${escapeHTML(headline)}</strong>
      <div class="helper-text">${escapeHTML(body)}</div>
    </article>
  `;
}

function mediaVideo(title, url, meta = "") {
  return `
    <article class="media-card">
      <strong>${escapeHTML(title)}</strong>
      ${meta ? `<div class="helper-text">${escapeHTML(meta)}</div>` : ""}
      <video src="${url}" controls preload="metadata"></video>
    </article>
  `;
}

function mediaImage(title, url, meta = "") {
  return `
    <article class="media-card">
      <strong>${escapeHTML(title)}</strong>
      ${meta ? `<div class="helper-text">${escapeHTML(meta)}</div>` : ""}
      <img src="${url}" alt="${escapeHTML(title)}" loading="lazy" />
    </article>
  `;
}

function summarizeProviders(values) {
  const unique = [...new Set(values.filter(Boolean))];
  return unique.length ? unique.join(" / ") : "未命中 fallback provider";
}

function truncate(value, length) {
  const text = String(value || "");
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

function normalizeRuntimeUrl(pathValue) {
  if (!pathValue) return "";
  const normalized = String(pathValue).replaceAll("\\", "/");
  if (normalized.startsWith("/runtime/")) return normalized;
  if (normalized.startsWith("runtime/")) return `/${normalized}`;
  return normalized.includes("/runtime/") ? normalized.slice(normalized.indexOf("/runtime/")) : normalized;
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

loadProjects().catch((error) => setStatus(error.message, "error"));
loadAutomationJobs().catch((error) => setStatus(error.message, "error"));
