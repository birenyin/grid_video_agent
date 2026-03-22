import { startTransition, useEffect, useMemo, useState } from "react";

import { AutomationDrawer, CreateDrawer } from "./components/Drawers";
import { Inspector } from "./components/Inspector";
import { ProjectSidebar } from "./components/ProjectSidebar";
import { Workbench } from "./components/Workbench";
import {
  AUTOMATION_FORM_DEFAULTS,
  CREATE_FORM_DEFAULTS,
  DEFAULT_REFERENCE_HINT,
  RENDER_FORM_DEFAULTS,
  buildArtifactEntries,
  buildMediaItems,
  buildPreviewPayload,
  clampShotDuration,
  computeDiagnostics,
  deepClone,
  getSelectedShot,
} from "./helpers";

const WORKFLOW_TAB_MAP = {
  script: "script",
  images: "visual",
  render: "voice",
};

const SIDEBAR_STORAGE_KEY = "grid-video-studio.sidebar-collapsed";

function readInitialSidebarState() {
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function buildRenderForm(project) {
  return {
    ...deepClone(RENDER_FORM_DEFAULTS),
    aspect_ratio: project?.content_input?.aspect_ratio || "9:16",
    render_mode: project?.artifacts?.last_render_mode || "video_audio",
    reference_image_path: project?.artifacts?.resolved_reference_image_path || "",
  };
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (typeof payload?.detail === "string") {
      throw new Error(payload.detail);
    }
    throw new Error(`Request failed with status ${response.status}`);
  }

  return payload;
}

export default function App() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState({ tone: "info", message: "React 工作台已就绪" });
  const [projectList, setProjectList] = useState([]);
  const [automationJobs, setAutomationJobs] = useState([]);
  const [projectDetail, setProjectDetail] = useState(null);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [selectedShotId, setSelectedShotId] = useState(null);
  const [workflowStep, setWorkflowStep] = useState("script");
  const [inspectorTab, setInspectorTab] = useState("script");
  const [previewMode, setPreviewMode] = useState("shot");
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [automationDrawerOpen, setAutomationDrawerOpen] = useState(false);
  const [createTab, setCreateTab] = useState("text");
  const [createForms, setCreateForms] = useState(() => deepClone(CREATE_FORM_DEFAULTS));
  const [automationForm, setAutomationForm] = useState(() => deepClone(AUTOMATION_FORM_DEFAULTS));
  const [renderForm, setRenderForm] = useState(() => deepClone(RENDER_FORM_DEFAULTS));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readInitialSidebarState);

  const selectedShot = useMemo(
    () => getSelectedShot(projectDetail, selectedShotId),
    [projectDetail, selectedShotId],
  );

  const diagnostics = useMemo(
    () => computeDiagnostics(projectDetail?.project, projectDetail?.attempts || []),
    [projectDetail],
  );
  const preview = useMemo(
    () => buildPreviewPayload(projectDetail, previewMode, selectedShotId),
    [projectDetail, previewMode, selectedShotId],
  );
  const artifactEntries = useMemo(
    () => buildArtifactEntries(projectDetail?.project, projectDetail?.asset_links),
    [projectDetail],
  );
  const mediaItems = useMemo(
    () => buildMediaItems(projectDetail?.project, projectDetail?.asset_links),
    [projectDetail],
  );

  useEffect(() => {
    document.title = "电网视频生成智能体";
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebarCollapsed ? "1" : "0");
    } catch {
      // Ignore storage failures in restricted environments.
    }
  }, [sidebarCollapsed]);

  useEffect(() => {
    void refreshAll();
  }, []);

  function setBusyState(nextBusy, message = null, tone = "info") {
    setBusy(nextBusy);
    if (message) {
      setStatus({ tone, message });
    }
  }

  function applyLoadedDetail(detail, preferredShotId = null) {
    const shotIds = detail?.project?.storyboard?.map((shot) => shot.shot_id) || [];
    const nextSelectedShotId = shotIds.includes(preferredShotId)
      ? preferredShotId
      : shotIds.includes(selectedShotId)
        ? selectedShotId
        : shotIds[0] || null;

    startTransition(() => {
      setProjectDetail(deepClone(detail));
      setSelectedProjectId(detail.project.project_id);
      setSelectedShotId(nextSelectedShotId);
      setRenderForm(buildRenderForm(detail.project));
    });
  }

  async function refreshAll(preferredProjectId = null) {
    setBusyState(true, "正在刷新项目和自动任务...");
    try {
      const [projects, jobs] = await Promise.all([
        fetchJSON("/projects?limit=50"),
        fetchJSON("/automation/jobs?limit=100"),
      ]);

      startTransition(() => {
        setProjectList(projects);
        setAutomationJobs(jobs);
      });

      const targetId = preferredProjectId || selectedProjectId || projects[0]?.project_id || null;
      if (targetId) {
        const detail = await fetchJSON(`/projects/${targetId}`);
        applyLoadedDetail(detail, selectedShotId);
      } else {
        startTransition(() => {
          setProjectDetail(null);
          setSelectedProjectId(null);
          setSelectedShotId(null);
          setRenderForm(deepClone(RENDER_FORM_DEFAULTS));
        });
      }

      setStatus({ tone: "success", message: "列表已刷新" });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function loadProject(projectId, preferredShotId = null) {
    setBusyState(true, "正在加载项目...");
    try {
      const detail = await fetchJSON(`/projects/${projectId}`);
      applyLoadedDetail(detail, preferredShotId);
      setStatus({ tone: "success", message: `项目 ${detail.project.project_id} 已加载` });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  function updateProject(mutator) {
    setProjectDetail((current) => {
      if (!current) return current;
      const next = deepClone(current);
      mutator(next);
      return next;
    });
  }

  function handleProjectFieldChange(field, value) {
    updateProject((next) => {
      if (field === "title") {
        next.project.content_input.title = value;
        if (next.project.summary) next.project.summary.title = value;
        if (next.project.script) next.project.script.title = value;
        return;
      }

      if (field === "summary") {
        if (next.project.summary) next.project.summary.summary = value;
        return;
      }

      if (field === "full_script") {
        next.project.content_input.raw_text = value;
        if (next.project.script) next.project.script.full_script = value;
        return;
      }

      next.project.content_input[field] = value;
    });

    if (field === "aspect_ratio") {
      setRenderForm((current) => ({ ...current, aspect_ratio: value }));
    }
  }

  function handleShotFieldChange(field, value) {
    updateProject((next) => {
      const shot = next.project.storyboard.find((item) => item.shot_id === selectedShotId);
      if (!shot) return;

      if (field === "shot_duration") {
        shot.shot_duration = clampShotDuration(value);
        return;
      }

      if (field === "visual_keywords") {
        shot.visual_keywords = String(value)
          .split(/[，,]/)
          .map((item) => item.trim())
          .filter(Boolean);
        return;
      }

      shot[field] = value;
    });
  }

  function handleDefaultReferenceChange(value) {
    updateProject((next) => {
      next.project.artifacts.resolved_reference_image_path = value;
    });

    setRenderForm((current) => ({
      ...current,
      reference_image_path: value || current.reference_image_path,
    }));
  }

  function handleShotReferenceChange(value) {
    updateProject((next) => {
      if (!selectedShotId) return;
      const map = next.project.artifacts.shot_reference_paths || {};
      if (value.trim()) {
        map[String(selectedShotId)] = value;
      } else {
        delete map[String(selectedShotId)];
      }
      next.project.artifacts.shot_reference_paths = map;
    });
  }

  function collectScriptPayload(regenerateStoryboard = false) {
    const project = projectDetail?.project;
    if (!project) return null;

    return {
      title: project.summary?.title || project.content_input.title || "未命名项目",
      full_script: project.script?.full_script || project.content_input.raw_text || "",
      summary: project.summary?.summary || "",
      mode: project.content_input.mode,
      target_duration_seconds: Number(project.content_input.target_duration_seconds || 60),
      aspect_ratio: project.content_input.aspect_ratio,
      regenerate_storyboard: regenerateStoryboard,
      storyboard: regenerateStoryboard ? [] : project.storyboard,
    };
  }

  function collectImagePayload(shotIds = []) {
    const project = projectDetail?.project;
    if (!project) return null;

    return {
      aspect_ratio: project.content_input.aspect_ratio,
      render_mode: renderForm.render_mode === "video_audio" ? "video_audio" : "image_audio",
      reference_image_path: project.artifacts.resolved_reference_image_path || DEFAULT_REFERENCE_HINT,
      shot_reference_overrides: project.artifacts.shot_reference_paths || {},
      shot_ids: shotIds,
    };
  }

  function collectRenderPayload() {
    return {
      preferred_voice: renderForm.preferred_voice,
      publish_mode: renderForm.publish_mode,
      render_mode: renderForm.render_mode,
      aspect_ratio: renderForm.aspect_ratio,
      reference_image_path:
        renderForm.reference_image_path ||
        projectDetail?.project?.artifacts?.resolved_reference_image_path ||
        DEFAULT_REFERENCE_HINT,
      reuse_existing_shot_images: renderForm.reuse_existing_shot_images,
    };
  }

  async function handleSaveScript(regenerateStoryboard = false) {
    if (!selectedProjectId) {
      setStatus({ tone: "danger", message: "请先选择一个项目" });
      return;
    }

    const payload = collectScriptPayload(regenerateStoryboard);
    if (!payload) return;

    setBusyState(true, regenerateStoryboard ? "正在重新拆分分镜..." : "正在保存文案...");
    try {
      const detail = await fetchJSON(`/projects/${selectedProjectId}/workflow/script`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      applyLoadedDetail(detail, regenerateStoryboard ? null : selectedShotId);
      setWorkflowStep("script");
      setInspectorTab("script");
      setStatus({
        tone: "success",
        message: regenerateStoryboard ? "分镜已重新生成" : "文案与分镜已保存",
      });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateImages(shotIds = []) {
    if (!selectedProjectId) {
      setStatus({ tone: "danger", message: "请先选择一个项目" });
      return;
    }

    const payload = collectImagePayload(shotIds);
    if (!payload) return;

    setBusyState(true, shotIds.length ? `正在生成镜头 ${shotIds.join(", ")} 的图片...` : "正在批量生成镜头图片...");
    try {
      const detail = await fetchJSON(`/projects/${selectedProjectId}/workflow/images`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      applyLoadedDetail(detail, selectedShotId);
      setWorkflowStep("images");
      setInspectorTab("visual");
      setPreviewMode("shot");
      setStatus({
        tone: "success",
        message: shotIds.length ? "当前镜头图片已更新" : "镜头图片已批量生成",
      });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleRender() {
    if (!selectedProjectId) {
      setStatus({ tone: "danger", message: "请先选择一个项目" });
      return;
    }

    setBusyState(true, "正在合成最终成片...");
    try {
      const response = await fetchJSON(`/projects/${selectedProjectId}/workflow/render`, {
        method: "POST",
        body: JSON.stringify(collectRenderPayload()),
      });

      await loadProject(selectedProjectId, selectedShotId);
      setWorkflowStep("render");
      setInspectorTab("output");
      setPreviewMode("final");
      setStatus({
        tone: "success",
        message: `成片已输出，本次累计 Provider 尝试 ${response.attempt_count} 次`,
      });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleOneClick() {
    if (!selectedProjectId) {
      setStatus({ tone: "danger", message: "请先选择一个项目" });
      return;
    }

    setBusyState(true, "正在一键执行完整流程...");
    try {
      const scriptDetail = await fetchJSON(`/projects/${selectedProjectId}/workflow/script`, {
        method: "PUT",
        body: JSON.stringify(collectScriptPayload(false)),
      });
      applyLoadedDetail(scriptDetail, selectedShotId);

      const imageDetail = await fetchJSON(`/projects/${selectedProjectId}/workflow/images`, {
        method: "POST",
        body: JSON.stringify({
          ...collectImagePayload([]),
          render_mode: renderForm.render_mode,
        }),
      });
      applyLoadedDetail(imageDetail, selectedShotId);

      const renderResponse = await fetchJSON(`/projects/${selectedProjectId}/workflow/render`, {
        method: "POST",
        body: JSON.stringify(collectRenderPayload()),
      });

      await loadProject(selectedProjectId, selectedShotId);
      setWorkflowStep("render");
      setInspectorTab("output");
      setPreviewMode("final");
      setStatus({
        tone: "success",
        message: `一键成片完成，累计 Provider 尝试 ${renderResponse.attempt_count} 次`,
      });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  function handleCreateFieldChange(section, field, value) {
    setCreateForms((current) => ({
      ...current,
      [section]: {
        ...current[section],
        [field]: value,
      },
    }));
  }

  async function handleCreateSubmit(section, endpoint) {
    setBusyState(true, "正在创建项目草稿...");
    try {
      const response = await fetchJSON(endpoint, {
        method: "POST",
        body: JSON.stringify(createForms[section]),
      });
      setCreateForms(deepClone(CREATE_FORM_DEFAULTS));
      setCreateDrawerOpen(false);
      await refreshAll(response.project_id);
      setStatus({ tone: "success", message: `项目 ${response.project_id} 已创建` });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  function handleAutomationFormChange(field, value) {
    setAutomationForm((current) => ({ ...current, [field]: value }));
  }

  async function handleAutomationSubmit() {
    setBusyState(true, "正在创建自动任务...");
    try {
      await fetchJSON("/automation/jobs", {
        method: "POST",
        body: JSON.stringify({
          ...automationForm,
          reference_image_path: automationForm.reference_image_path || DEFAULT_REFERENCE_HINT,
        }),
      });
      setAutomationForm(deepClone(AUTOMATION_FORM_DEFAULTS));
      const jobs = await fetchJSON("/automation/jobs?limit=100");
      startTransition(() => setAutomationJobs(jobs));
      setStatus({ tone: "success", message: "自动任务已创建" });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleRunAutomation(jobId) {
    setBusyState(true, "自动任务执行中...");
    try {
      const run = await fetchJSON(`/automation/jobs/${jobId}/run`, { method: "POST" });
      const jobs = await fetchJSON("/automation/jobs?limit=100");
      startTransition(() => setAutomationJobs(jobs));
      if (run.project_id) {
        await refreshAll(run.project_id);
      }
      setStatus({ tone: "success", message: `自动任务执行完成：${run.status}` });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleAutomation(jobId, nextStatus) {
    setBusyState(true, "正在更新自动任务状态...");
    try {
      await fetchJSON(`/automation/jobs/${jobId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: nextStatus }),
      });
      const jobs = await fetchJSON("/automation/jobs?limit=100");
      startTransition(() => setAutomationJobs(jobs));
      setStatus({ tone: "success", message: "自动任务状态已更新" });
    } catch (error) {
      setStatus({ tone: "danger", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  function handleWorkflowStepChange(step) {
    setWorkflowStep(step);
    setInspectorTab(WORKFLOW_TAB_MAP[step] || "script");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <div className="brand-mark" />
          <div>
            <div className="brand-kicker">GRID DISPATCH STUDIO</div>
            <h1>电网视频生成智能体</h1>
          </div>
        </div>

        <div className={`header-status ${status.tone}`}>
          <span>{busy ? "处理中" : "系统状态"}</span>
          <strong>{status.message}</strong>
        </div>

        <div className="header-actions">
          <button type="button" className="ghost-button" onClick={() => setSidebarCollapsed((current) => !current)}>
            {sidebarCollapsed ? "展开项目库" : "收起项目库"}
          </button>
          <button type="button" className="ghost-button" onClick={() => setCreateDrawerOpen(true)}>
            新建项目
          </button>
          <button type="button" className="ghost-button" onClick={() => setAutomationDrawerOpen(true)}>
            自动任务
          </button>
          <button type="button" className="ghost-button" disabled={busy} onClick={() => refreshAll(selectedProjectId)}>
            刷新
          </button>
          <button type="button" className="primary-button" disabled={busy || !selectedProjectId} onClick={handleOneClick}>
            一键成片
          </button>
        </div>
      </header>

      <div className={`studio-layout ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <ProjectSidebar
          busy={busy}
          collapsed={sidebarCollapsed}
          projectList={projectList}
          selectedProjectId={selectedProjectId}
          projectDetail={projectDetail}
          onSelectProject={(projectId) => loadProject(projectId)}
          onOpenCreate={() => setCreateDrawerOpen(true)}
          onOpenAutomation={() => setAutomationDrawerOpen(true)}
          onToggleCollapse={() => setSidebarCollapsed((current) => !current)}
        />

        <Workbench
          busy={busy}
          projectDetail={projectDetail}
          preview={preview}
          previewMode={previewMode}
          onPreviewModeChange={setPreviewMode}
          workflowStep={workflowStep}
          onWorkflowStepChange={handleWorkflowStepChange}
          diagnostics={diagnostics}
          selectedShotId={selectedShotId}
          onSelectShot={setSelectedShotId}
          onRunOneClick={handleOneClick}
        />

        <Inspector
          busy={busy}
          projectDetail={projectDetail}
          selectedShot={selectedShot}
          inspectorTab={inspectorTab}
          renderForm={renderForm}
          artifactEntries={artifactEntries}
          mediaItems={mediaItems}
          onTabChange={setInspectorTab}
          onProjectFieldChange={handleProjectFieldChange}
          onShotFieldChange={handleShotFieldChange}
          onDefaultReferenceChange={handleDefaultReferenceChange}
          onShotReferenceChange={handleShotReferenceChange}
          onSaveScript={handleSaveScript}
          onRegenerateStoryboard={() => handleSaveScript(true)}
          onGenerateCurrent={() => handleGenerateImages(selectedShot ? [selectedShot.shot_id] : [])}
          onGenerateAll={() => handleGenerateImages([])}
          onRenderFieldChange={(field, value) => setRenderForm((current) => ({ ...current, [field]: value }))}
          onRender={handleRender}
        />
      </div>

      <CreateDrawer
        open={createDrawerOpen}
        busy={busy}
        createTab={createTab}
        createForms={createForms}
        onClose={() => setCreateDrawerOpen(false)}
        onTabChange={setCreateTab}
        onFieldChange={handleCreateFieldChange}
        onSubmit={handleCreateSubmit}
      />

      <AutomationDrawer
        open={automationDrawerOpen}
        busy={busy}
        form={automationForm}
        jobs={automationJobs}
        onClose={() => setAutomationDrawerOpen(false)}
        onFieldChange={handleAutomationFormChange}
        onSubmit={handleAutomationSubmit}
        onRunNow={handleRunAutomation}
        onToggleStatus={handleToggleAutomation}
      />
    </div>
  );
}
