const state = {
  selectedProjectId: null,
};

const statusEl = document.getElementById("global-status");
const projectListEl = document.getElementById("project-list");
const detailTitleEl = document.getElementById("detail-title");
const detailBadgesEl = document.getElementById("detail-badges");
const detailEmptyEl = document.getElementById("detail-empty");
const detailContentEl = document.getElementById("detail-content");
const diagnosticsPanelEl = document.getElementById("diagnostics-panel");
const summaryBlockEl = document.getElementById("summary-block");
const scriptBlockEl = document.getElementById("script-block");
const artifactLinksEl = document.getElementById("artifact-links");
const mediaGalleryEl = document.getElementById("media-gallery");
const storyboardListEl = document.getElementById("storyboard-list");
const attemptTableEl = document.getElementById("attempt-table");
const renderFormEl = document.getElementById("form-render");
const refreshProjectsButton = document.getElementById("refresh-projects");
const renderButton = document.getElementById("render-button");
const automationListEl = document.getElementById("automation-list");

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".pane").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.pane).classList.add("active");
  });
});

refreshProjectsButton.addEventListener("click", () => loadProjects(state.selectedProjectId));

bindCreateForm("form-create-text", "/projects/create_from_text", {
  content_text: "string",
  target_duration_seconds: "number",
});

bindCreateForm("form-create-script", "/projects/create_from_script", {
  full_script: "string",
  target_duration_seconds: "number",
});

bindCreateForm("form-create-url", "/projects/create_from_url", {
  target_duration_seconds: "number",
});

bindCreateForm("form-create-feed", "/projects/create_from_rpa_feed", {
  target_duration_seconds: "number",
  render_preview_bundle: "checkbox",
});

bindAutomationForm();

renderFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedProjectId) {
    setStatus("请先选择一个项目。", true);
    return;
  }

  const payload = formToJSON(renderFormEl, {
    aspect_ratio: "nullable-string",
  });
  setBusy(true, "开始渲染项目，这一步可能需要几分钟。");
  try {
    const response = await fetchJSON(`/projects/${state.selectedProjectId}/render`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus(`渲染完成，Provider 尝试次数：${response.attempt_count}`);
    await loadProjects(state.selectedProjectId);
    await loadProject(state.selectedProjectId);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    setBusy(false);
  }
});

async function bindCreateForm(formId, endpoint, typeMap) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formToJSON(form, typeMap);
    setBusy(true, "正在创建项目草稿...");
    try {
      const response = await fetchJSON(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      form.reset();
      if (formId === "form-create-feed") {
        form.querySelector("[name='render_preview_bundle']").checked = true;
      }
      setStatus(`项目 ${response.project_id} 创建成功。`);
      state.selectedProjectId = response.project_id;
      await loadProjects(response.project_id);
      await loadProject(response.project_id);
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      setBusy(false);
    }
  });
}

function bindAutomationForm() {
  const form = document.getElementById("form-create-automation");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formToJSON(form, {
      interval_minutes: "number",
      target_duration_seconds: "number",
      per_source_limit: "number",
      total_fetch_limit: "number",
      auto_render: "checkbox",
      reference_image_path: "nullable-string",
    });
    setBusy(true, "Creating automation job...");
    try {
      await fetchJSON("/automation/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      form.reset();
      form.querySelector("[name='auto_render']").checked = true;
      setStatus("Automation job created.");
      await loadAutomationJobs();
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      setBusy(false);
    }
  });
}

function formToJSON(form, typeMap = {}) {
  const payload = {};
  const formData = new FormData(form);
  for (const [key, rawValue] of formData.entries()) {
    const strategy = typeMap[key];
    if (strategy === "number") {
      payload[key] = Number(rawValue);
      continue;
    }
    if (strategy === "nullable-string") {
      payload[key] = String(rawValue || "").trim() || null;
      continue;
    }
    payload[key] = typeof rawValue === "string" ? rawValue.trim() : rawValue;
  }

  for (const [key, strategy] of Object.entries(typeMap)) {
    if (strategy !== "checkbox") {
      continue;
    }
    const field = form.querySelector(`[name="${key}"]`);
    payload[key] = Boolean(field && field.checked);
  }

  return payload;
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

function setBusy(isBusy, message = "") {
  renderButton.disabled = isBusy;
  document.querySelectorAll("button").forEach((button) => {
    if (button.classList.contains("tab-button")) {
      return;
    }
    button.disabled = isBusy;
  });
  if (message) {
    statusEl.textContent = message;
  }
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.background = isError
    ? "linear-gradient(135deg, #9d3d2f, #c76b57)"
    : "linear-gradient(135deg, #184861, #0f6c82)";
}

async function loadProjects(preferredProjectId = null) {
  const items = await fetchJSON("/projects?limit=50");
  renderProjectList(items);

  const targetId =
    preferredProjectId ||
    state.selectedProjectId ||
    (items.length > 0 ? items[0].project_id : null);

  if (targetId) {
    state.selectedProjectId = targetId;
    await loadProject(targetId);
  } else {
    renderEmptyState();
  }
}

async function loadAutomationJobs() {
  const jobs = await fetchJSON("/automation/jobs?limit=100");
  renderAutomationJobs(jobs);
}

function renderAutomationJobs(jobs) {
  if (!jobs.length) {
    automationListEl.innerHTML = `<div class="automation-card"><strong>No automation jobs yet.</strong><div class="automation-meta">Create one above to start scheduled fetch -> project -> render runs.</div></div>`;
    return;
  }

  automationListEl.innerHTML = jobs
    .map((job) => {
      const nextRun = job.next_run_at ? new Date(job.next_run_at).toLocaleString() : "N/A";
      const lastRun = job.last_run_at ? new Date(job.last_run_at).toLocaleString() : "Never";
      const runButtonLabel = job.status === "paused" ? "Run Once" : "Run Now";
      const toggleLabel = job.status === "paused" ? "Resume" : "Pause";
      return `
        <article class="automation-card">
          <strong>${escapeHTML(job.name)}</strong>
          <div class="automation-meta">
            <span>${escapeHTML(job.job_id)} · ${escapeHTML(job.status)}</span>
            <span>${escapeHTML(job.fetch.source_set)} · every ${escapeHTML(String(job.interval_minutes))} min</span>
            <span>Last run: ${escapeHTML(lastRun)}</span>
            <span>Next run: ${escapeHTML(nextRun)}</span>
            <span>Last project: ${escapeHTML(job.last_project_id || "None")}</span>
            ${job.last_error ? `<span>Error: ${escapeHTML(job.last_error)}</span>` : ""}
          </div>
          <div class="automation-actions">
            <button class="small-button" type="button" data-automation-run="${job.job_id}">${runButtonLabel}</button>
            <button class="small-button" type="button" data-automation-toggle="${job.job_id}" data-next-status="${job.status === "paused" ? "active" : "paused"}">${toggleLabel}</button>
          </div>
        </article>
      `;
    })
    .join("");

  automationListEl.querySelectorAll("[data-automation-run]").forEach((button) => {
    button.addEventListener("click", async () => {
      const jobId = button.dataset.automationRun;
      setBusy(true, "Running automation job...");
      try {
        const run = await fetchJSON(`/automation/jobs/${jobId}/run`, {
          method: "POST",
        });
        setStatus(`Automation finished: ${run.status}`);
        if (run.project_id) {
          state.selectedProjectId = run.project_id;
          await loadProjects(run.project_id);
          await loadProject(run.project_id);
        }
        await loadAutomationJobs();
      } catch (error) {
        setStatus(error.message, true);
        await loadAutomationJobs();
      } finally {
        setBusy(false);
      }
    });
  });

  automationListEl.querySelectorAll("[data-automation-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      const jobId = button.dataset.automationToggle;
      const nextStatus = button.dataset.nextStatus;
      setBusy(true, "Updating automation status...");
      try {
        await fetchJSON(`/automation/jobs/${jobId}/status`, {
          method: "POST",
          body: JSON.stringify({ status: nextStatus }),
        });
        setStatus(`Automation job set to ${nextStatus}.`);
        await loadAutomationJobs();
      } catch (error) {
        setStatus(error.message, true);
      } finally {
        setBusy(false);
      }
    });
  });
}

function renderProjectList(items) {
  if (!items.length) {
    projectListEl.innerHTML = `<div class="project-item"><strong>还没有项目</strong><span>先在右侧创建一个草稿。</span></div>`;
    return;
  }

  projectListEl.innerHTML = items
    .map((item) => {
      const activeClass = item.project_id === state.selectedProjectId ? "active" : "";
      return `
        <button class="project-item ${activeClass}" type="button" data-project-id="${item.project_id}">
          <strong>${escapeHTML(item.title)}</strong>
          <span>${escapeHTML(item.project_id)} · ${escapeHTML(item.status)}</span>
          <span>${escapeHTML(item.mode)} · ${escapeHTML(item.source_type)}</span>
        </button>
      `;
    })
    .join("");

  projectListEl.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.selectedProjectId = button.dataset.projectId;
      renderProjectList(items);
      await loadProject(button.dataset.projectId);
    });
  });
}

async function loadProject(projectId) {
  const detail = await fetchJSON(`/projects/${projectId}`);
  renderProjectDetail(detail);
}

function renderProjectDetail(detail) {
  const { project, attempts, asset_links: assetLinks } = detail;
  detailEmptyEl.classList.add("hidden");
  detailContentEl.classList.remove("hidden");

  detailTitleEl.textContent = project.summary ? project.summary.title : project.project_id;
  detailBadgesEl.innerHTML = [
    badge(project.status, project.status === "failed"),
    badge(project.content_input.mode),
    badge(project.content_input.aspect_ratio),
    badge(project.content_input.source_type),
  ].join("");

  diagnosticsPanelEl.innerHTML = renderDiagnostics(project, attempts);
  summaryBlockEl.innerHTML = renderSummary(project);
  scriptBlockEl.textContent = project.script ? project.script.full_script : "";
  artifactLinksEl.innerHTML = renderArtifactLinks(project, assetLinks);
  mediaGalleryEl.innerHTML = renderMediaGallery(project, assetLinks);
  storyboardListEl.innerHTML = renderStoryboard(project.storyboard);
  attemptTableEl.innerHTML = renderAttempts(attempts);
  syncRenderForm(project);
}

function renderSummary(project) {
  const bulletPoints = (project.summary?.bullet_points || [])
    .map((item) => `<li>${escapeHTML(item)}</li>`)
    .join("");
  const warnings = (project.warnings || [])
    .map((item) => `<li>${escapeHTML(item)}</li>`)
    .join("");

  return `
    <ul class="summary-list">
      <li><strong>摘要：</strong>${escapeHTML(project.summary?.summary || "")}</li>
      <li><strong>创建时间：</strong>${escapeHTML(project.created_at)}</li>
      <li><strong>工作目录：</strong>${escapeHTML(project.artifacts.working_dir)}</li>
      <li><strong>镜头数：</strong>${project.storyboard.length}</li>
    </ul>
    ${bulletPoints ? `<h4>重点提炼</h4><ul class="summary-list">${bulletPoints}</ul>` : ""}
    ${warnings ? `<h4>提醒</h4><ul class="summary-list">${warnings}</ul>` : ""}
  `;
}

function renderDiagnostics(project, attempts) {
  const shotVideos = project.artifacts?.shot_videos || [];
  const shotImages = project.artifacts?.shot_images || [];
  const failedAttempts = attempts.filter((item) => item.status === "failed");
  const failedVideoAttempts = failedAttempts.filter((item) => item.action_name.includes("generate_video"));
  const failedImageAttempts = failedAttempts.filter((item) => item.action_name.includes("generate_reference_image"));
  const fallbackVideos = shotVideos.filter(
    (item) => item.used_fallback || ["mock_video", "static_image_video"].includes(item.provider_name)
  );
  const fallbackImages = shotImages.filter(
    (item) => item.used_fallback || ["mock_image", "newsroom_preview"].includes(item.provider_name)
  );
  const latestFailedAttempt = [...failedAttempts].sort((left, right) =>
    String(right.created_at).localeCompare(String(left.created_at))
  )[0];
  const cards = [];

  if (project.status === "rendering") {
    cards.push(
      diagnosticCard(
        "渲染状态",
        "warning",
        "项目仍在处理中",
        "如果终端主要在打印 304 / 206，多半只是浏览器在读取缓存或播放视频，不是后台重复生成。"
      )
    );
  } else if (project.status === "failed") {
    cards.push(
      diagnosticCard(
        "渲染状态",
        "danger",
        "本次渲染失败",
        "先看下面最近一次错误和 Provider 调用记录，页面现在会明确标出失败与回退。"
      )
    );
  } else if (project.status === "rendered") {
    cards.push(
      diagnosticCard(
        "渲染状态",
        "success",
        "项目已渲染完成",
        "可以直接预览成片、镜头视频和镜头图。"
      )
    );
  }

  cards.push(
    diagnosticCard(
      "渲染配置",
      "info",
      `${project.artifacts?.last_render_mode || "未记录"} · ${project.content_input.aspect_ratio}`,
      `镜头数 ${project.storyboard.length}，来源 ${project.content_input.source_type}。`
    )
  );

  if (project.artifacts?.resolved_reference_image_path) {
    cards.push(
      diagnosticCard(
        "参考图",
        "success",
        "本次渲染已使用参考人物图",
        project.artifacts.resolved_reference_image_path
      )
    );
  } else {
    cards.push(
      diagnosticCard(
        "参考图",
        "warning",
        "这次没有可用参考图",
        "系统会尝试默认人物图；如果默认图和上传图都不可用，就只能回退到预览帧或占位方案。"
      )
    );
  }

  if (failedVideoAttempts.length) {
    cards.push(
      diagnosticCard(
        "视频接口",
        "danger",
        `真实视频接口失败 ${failedVideoAttempts.length} 次`,
        "你现在看到的静态镜头、文字卡片或静态图视频，通常就是这里失败后触发的回退结果。"
      )
    );
  }

  if (failedImageAttempts.length) {
    cards.push(
      diagnosticCard(
        "图片接口",
        "danger",
        `真实图片接口失败 ${failedImageAttempts.length} 次`,
        "镜头图没有正常生成时，系统会继续尝试 mock 图或 newsroom 预览帧。"
      )
    );
  }

  if (fallbackVideos.length) {
    cards.push(
      diagnosticCard(
        "视频回退",
        "warning",
        `${fallbackVideos.length} 个镜头使用了回退视频`,
        `当前回退 Provider：${summarizeProviders(fallbackVideos.map((item) => item.provider_name))}。`
      )
    );
  }

  if (fallbackImages.length) {
    cards.push(
      diagnosticCard(
        "图片回退",
        "warning",
        `${fallbackImages.length} 个镜头使用了回退图片`,
        `当前回退 Provider：${summarizeProviders(fallbackImages.map((item) => item.provider_name))}。`
      )
    );
  }

  if (latestFailedAttempt) {
    cards.push(
      diagnosticCard(
        "最近错误",
        "danger",
        `${latestFailedAttempt.provider_name} / ${latestFailedAttempt.action_name}`,
        latestFailedAttempt.error_message || "未返回错误详情。"
      )
    );
  }

  return cards.join("");
}

function renderArtifactLinks(project, assetLinks) {
  const entries = [
    ["summary.json", normalizeRuntimeUrl(project.artifacts.summary_path)],
    ["script.json", normalizeRuntimeUrl(project.artifacts.script_path)],
    ["storyboard.json", normalizeRuntimeUrl(project.artifacts.storyboard_path)],
    ["news_plan.json", normalizeRuntimeUrl(project.artifacts.news_plan_path)],
    ["run_report.json", normalizeRuntimeUrl(project.artifacts.news_report_path)],
    ["selected_sources.md", normalizeRuntimeUrl(project.artifacts.selected_sources_path)],
    ["subtitles.srt", assetLinks.subtitle_url],
    ["publish_payload.json", assetLinks.publish_payload_url],
  ].filter((item) => item[1]);

  if (!entries.length) {
    return `<div class="link-card">当前项目还没有可浏览的文件。</div>`;
  }

  return entries
    .map(
      ([label, url]) => `
        <div class="link-card">
          <strong>${escapeHTML(label)}</strong>
          <div><a href="${url}" target="_blank" rel="noreferrer">${escapeHTML(url)}</a></div>
        </div>
      `
    )
    .join("");
}

function renderMediaGallery(project, assetLinks) {
  const cards = [];
  const shotImages = project.artifacts?.shot_images || [];
  const shotVideos = project.artifacts?.shot_videos || [];

  if (assetLinks.final_video_url) {
    cards.push(mediaVideo("最终成片", assetLinks.final_video_url));
  }
  if (assetLinks.preview_video_url) {
    cards.push(mediaVideo("RPA 预览 MP4", assetLinks.preview_video_url));
  }
  if (assetLinks.preview_gif_url) {
    cards.push(mediaImage("RPA 预览 GIF", assetLinks.preview_gif_url));
  }
  if (assetLinks.preview_cover_url) {
    cards.push(mediaImage("RPA 预览封面", assetLinks.preview_cover_url));
  }

  shotImages.slice(0, 6).forEach((item, index) => {
    const url = normalizeRuntimeUrl(item.image_path);
    if (!url) {
      return;
    }
    cards.push(
      mediaImage(
        `镜头图 ${item.shot_id || index + 1}`,
        url,
        `${item.provider_name}${item.used_fallback ? " · fallback" : ""}`
      )
    );
  });
  shotVideos.slice(0, 4).forEach((item, index) => {
    const url = normalizeRuntimeUrl(item.video_path);
    if (!url) {
      return;
    }
    cards.push(
      mediaVideo(
        `镜头视频 ${item.shot_id || index + 1}`,
        url,
        `${item.provider_name}${item.used_fallback ? " · fallback" : ""}`
      )
    );
  });

  if (!cards.length) {
    return `<div class="media-card">当前项目还没有可预览的图片或视频。</div>`;
  }

  return cards.join("");
}

function renderStoryboard(storyboard) {
  if (!storyboard.length) {
    return `<div class="storyboard-card">当前项目还没有分镜数据。</div>`;
  }

  return storyboard
    .map(
      (shot) => `
        <article class="storyboard-card">
          <h4>镜头 ${shot.shot_id} · ${shot.shot_duration}s</h4>
          <p><strong>口播：</strong>${escapeHTML(shot.narration_text)}</p>
          <p><strong>字幕：</strong>${escapeHTML(shot.subtitle_text)}</p>
          <p><strong>画面：</strong>${escapeHTML(shot.visual_prompt_cn)}</p>
        </article>
      `
    )
    .join("");
}

function renderAttempts(attempts) {
  if (!attempts.length) {
    return `<div class="link-card">当前项目还没有 provider 调用记录。</div>`;
  }

  const rows = attempts
    .map((item) => {
      const rowClass =
        item.status === "failed"
          ? "failed-row"
          : ["mock_video", "mock_image", "static_image_video", "newsroom_preview"].includes(item.provider_name)
            ? "fallback-row"
            : "";
      const statusClass = item.status === "failed" ? "failed" : "success";
      return `
        <tr class="${rowClass}">
          <td>${escapeHTML(item.created_at)}</td>
          <td>${escapeHTML(item.provider_name)}</td>
          <td>${escapeHTML(item.action_name)}</td>
          <td>${escapeHTML(String(item.attempt_no))}</td>
          <td><span class="status-pill ${statusClass}">${escapeHTML(item.status)}</span></td>
          <td>${escapeHTML(item.error_message || "—")}</td>
        </tr>
      `;
    })
    .join("");

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

function syncRenderForm(project) {
  renderFormEl.querySelector("[name='aspect_ratio']").value = project.content_input.aspect_ratio || "";
  renderFormEl.querySelector("[name='reference_image_path']").value =
    project.artifacts?.resolved_reference_image_path || "";
}

function renderEmptyState() {
  detailTitleEl.textContent = "请选择左侧项目";
  detailBadgesEl.innerHTML = "";
  detailContentEl.classList.add("hidden");
  detailEmptyEl.classList.remove("hidden");
}

function badge(text, isFailed = false) {
  return `<span class="badge ${isFailed ? "badge-failed" : ""}">${escapeHTML(text)}</span>`;
}

function mediaVideo(title, url, meta = "") {
  return `
    <article class="media-card">
      <strong>${escapeHTML(title)}</strong>
      ${meta ? `<div class="media-meta">${escapeHTML(meta)}</div>` : ""}
      <video src="${url}" controls preload="metadata"></video>
    </article>
  `;
}

function mediaImage(title, url, meta = "") {
  return `
    <article class="media-card">
      <strong>${escapeHTML(title)}</strong>
      ${meta ? `<div class="media-meta">${escapeHTML(meta)}</div>` : ""}
      <img src="${url}" alt="${escapeHTML(title)}" loading="lazy" />
    </article>
  `;
}

function diagnosticCard(label, tone, headline, body) {
  return `
    <article class="diagnostic-card ${tone}">
      <span class="diagnostic-label">${escapeHTML(label)}</span>
      <strong>${escapeHTML(headline)}</strong>
      <p>${escapeHTML(body)}</p>
    </article>
  `;
}

function summarizeProviders(values) {
  const unique = [...new Set(values.filter(Boolean))];
  return unique.length ? unique.join(" / ") : "未命中回退 Provider";
}

function normalizeRuntimeUrl(pathValue) {
  if (!pathValue) {
    return "";
  }
  const normalized = String(pathValue).replaceAll("\\", "/");
  if (normalized.startsWith("/runtime/")) {
    return normalized;
  }
  if (normalized.startsWith("runtime/")) {
    return `/${normalized}`;
  }
  const marker = "/runtime/";
  if (normalized.includes(marker)) {
    return normalized.slice(normalized.indexOf(marker));
  }
  return "";
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

loadProjects().catch((error) => {
  setStatus(error.message, true);
});

loadAutomationJobs().catch((error) => {
  setStatus(error.message, true);
});
