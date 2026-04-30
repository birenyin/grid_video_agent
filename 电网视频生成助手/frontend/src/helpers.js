export const DEFAULT_REFERENCE_HINT = "F:\\AICODING\\需求\\电网人物形象.png";

export const CREATE_FORM_DEFAULTS = {
  text: {
    title: "",
    content_text: "",
    source_url: "",
    mode: "news_mode",
    target_duration_seconds: 60,
    aspect_ratio: "9:16",
  },
  script: {
    title: "",
    full_script: "",
    mode: "explain_mode",
    target_duration_seconds: 60,
    aspect_ratio: "9:16",
  },
  url: {
    source_url: "",
    title: "",
    mode: "news_mode",
    target_duration_seconds: 60,
    aspect_ratio: "9:16",
  },
  feed: {
    feed_path: "",
    title: "",
    plan_mode: "rule",
    mode: "news_mode",
    target_duration_seconds: 60,
    aspect_ratio: "9:16",
    render_preview_bundle: true,
  },
};

export const AUTOMATION_FORM_DEFAULTS = {
  name: "",
  source_set: "mixed",
  focus_topics: [],
  interval_minutes: 240,
  plan_mode: "rule",
  per_source_limit: 3,
  total_fetch_limit: 8,
  mode: "news_mode",
  target_duration_seconds: 60,
  aspect_ratio: "9:16",
  render_mode: "image_audio",
  preferred_voice: "professional_cn_male",
  publish_mode: "draft",
  reference_image_path: "",
  auto_render: true,
};

export const RENDER_FORM_DEFAULTS = {
  preferred_voice: "professional_cn_male",
  publish_mode: "draft",
  render_mode: "video_audio",
  video_generation_mode: "image_to_video",
  aspect_ratio: "9:16",
  reference_image_path: "",
  reuse_existing_shot_images: true,
  reuse_existing_shot_videos: true,
};

export const INSPECTOR_TABS = [
  { key: "script", label: "文案" },
  { key: "visual", label: "画面" },
  { key: "video", label: "转视频" },
  { key: "role", label: "角色" },
  { key: "voice", label: "配音" },
  { key: "music", label: "音乐" },
  { key: "output", label: "输出" },
];

export function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function normalizeRuntimeUrl(pathValue) {
  if (!pathValue) return "";
  const normalized = String(pathValue).replaceAll("\\", "/");
  if (normalized.startsWith("/runtime/")) return normalized;
  if (normalized.startsWith("runtime/")) return `/${normalized}`;
  return normalized.includes("/runtime/") ? normalized.slice(normalized.indexOf("/runtime/")) : normalized;
}

export function truncateText(value, length = 80) {
  const text = String(value || "");
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

export function clampShotDuration(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 4;
  return Math.min(6, Math.max(3, Math.round(numeric)));
}

export function formatDuration(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total)) return "--";
  const rounded = Math.max(0, Math.round(total));
  const minutes = Math.floor(rounded / 60);
  const remainder = rounded % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export function getProjectTitle(project) {
  if (!project) return "请选择一个项目";
  return project.summary?.title || project.content_input?.title || project.project_id;
}

export function getSelectedShot(projectDetail, selectedShotId) {
  return projectDetail?.project?.storyboard?.find((shot) => shot.shot_id === selectedShotId) || null;
}

export function findShotImage(projectDetail, shotId) {
  return projectDetail?.project?.artifacts?.shot_images?.find((item) => item.shot_id === shotId) || null;
}

export function findShotVideo(projectDetail, shotId) {
  return projectDetail?.project?.artifacts?.shot_videos?.find((item) => item.shot_id === shotId) || null;
}

export function getShotThumbUrl(projectDetail, shotId) {
  const shotVideo = findShotVideo(projectDetail, shotId);
  const shotImage = findShotImage(projectDetail, shotId);
  if (shotVideo) {
    return normalizeRuntimeUrl(shotVideo.poster_path || shotVideo.video_path);
  }
  if (shotImage) {
    return normalizeRuntimeUrl(shotImage.image_path);
  }
  return "";
}

export function summarizeProviders(values) {
  const unique = [...new Set(values.filter(Boolean))];
  return unique.length ? unique.join(" / ") : "未命中 fallback";
}

export function computeDiagnostics(project, attempts) {
  if (!project) return [];

  const failedAttempts = (attempts || []).filter((item) => item.status === "failed");
  const failedVideoAttempts = failedAttempts.filter((item) => item.action_name.includes("generate_video"));
  const fallbackVideos = (project.artifacts?.shot_videos || []).filter(
    (item) => item.used_fallback || ["mock_video", "static_image_video"].includes(item.provider_name),
  );
  const fallbackImages = (project.artifacts?.shot_images || []).filter(
    (item) => item.used_fallback || ["mock_image", "newsroom_preview"].includes(item.provider_name),
  );
  const latestError = [...failedAttempts].sort((left, right) =>
    String(right.created_at).localeCompare(String(left.created_at)),
  )[0];

  const cards = [
    {
      label: "项目状态",
      tone: project.status === "failed" ? "danger" : project.status === "rendered" ? "success" : "warning",
      headline:
        project.status === "failed"
          ? "当前项目有失败步骤"
          : project.status === "rendered"
            ? "项目已完成成片输出"
            : "项目还在草稿或处理中",
      body:
        project.status === "rendering"
          ? "终端里出现 304 或 206 往往只是浏览器在读缓存或分段播放，不代表后台仍在生成。"
          : "状态会随着文案、图片和成片步骤推进实时更新。",
    },
    {
      label: "参考图",
      tone: project.artifacts?.resolved_reference_image_path ? "success" : "warning",
      headline: project.artifacts?.resolved_reference_image_path ? "当前项目已锁定参考人物图" : "当前项目未手动上传参考图",
      body: project.artifacts?.resolved_reference_image_path || `系统会默认使用 ${DEFAULT_REFERENCE_HINT}`,
    },
    {
      label: "镜头图片",
      tone: fallbackImages.length ? "warning" : "success",
      headline: `${project.artifacts?.shot_images?.length || 0}/${project.storyboard?.length || 0} 个镜头已有图片`,
      body: fallbackImages.length
        ? `其中 ${fallbackImages.length} 个镜头使用了 fallback 图片：${summarizeProviders(fallbackImages.map((item) => item.provider_name))}`
        : "第二步镜头图已经齐了，可以继续做最终合成。",
    },
    {
      label: "镜头视频",
      tone: failedVideoAttempts.length || fallbackVideos.length ? "warning" : "success",
      headline: failedVideoAttempts.length ? `真实视频接口失败 ${failedVideoAttempts.length} 次` : "当前没有视频接口失败记录",
      body: fallbackVideos.length
        ? `有 ${fallbackVideos.length} 个镜头自动回退成静态图视频，所以会出现“只有字或画面不动”的情况。`
        : "当前镜头视频状态正常。",
    },
  ];

  if (latestError) {
    cards.push({
      label: "最近错误",
      tone: "danger",
      headline: `${latestError.provider_name} / ${latestError.action_name}`,
      body: latestError.error_message || "没有更详细的错误信息",
    });
  }

  return cards;
}

export function buildPreviewPayload(projectDetail, previewMode, selectedShotId) {
  if (!projectDetail?.project) {
    return {
      kind: "placeholder",
      title: "当前还没有可预览内容",
      subtitle: "请先创建项目或从左侧选择已有项目。",
      provider: "等待素材",
      duration: "--",
      aspectRatio: "16:9",
    };
  }

  const { project, asset_links: assetLinks } = projectDetail;
  const shot = getSelectedShot(projectDetail, selectedShotId);
  const aspectRatio = shot?.aspect_ratio || project.content_input?.aspect_ratio || "16:9";
  const totalDuration = formatDuration(
    (project.storyboard || []).reduce((sum, item) => sum + Number(item.shot_duration || 0), 0),
  );

  if (previewMode === "final" && assetLinks?.final_video_url) {
    return {
      kind: "video",
      url: assetLinks.final_video_url,
      title: "最终成片",
      subtitle: "这里显示最终输出的视频成片。",
      provider: project.artifacts?.composition?.provider_name || "final_video",
      duration: totalDuration,
      aspectRatio,
    };
  }

  if (previewMode === "preview") {
    const previewUrl =
      assetLinks?.preview_video_url || assetLinks?.preview_gif_url || assetLinks?.preview_cover_url || "";
    if (previewUrl) {
      return {
        kind: previewUrl.endsWith(".mp4") ? "video" : "image",
        url: previewUrl,
        title: "RPA 预览",
        subtitle: "这里显示自动抓取链路生成的 newsroom 预览包。",
        provider: "newsroom_preview",
        duration: totalDuration,
        aspectRatio,
      };
    }
  }

  if (shot) {
    const shotVideo = findShotVideo(projectDetail, shot.shot_id);
    const shotImage = findShotImage(projectDetail, shot.shot_id);
    if (shotVideo) {
      return {
        kind: "video",
        url: normalizeRuntimeUrl(shotVideo.video_path),
        title: `镜头 ${shot.shot_id}`,
        subtitle: shot.narration_text || shot.subtitle_text || "当前镜头暂无文案。",
        provider: `${shotVideo.provider_name}${shotVideo.used_fallback ? " / fallback" : ""}`,
        duration: formatDuration(shot.shot_duration),
        aspectRatio,
      };
    }
    if (shotImage) {
      return {
        kind: "image",
        url: normalizeRuntimeUrl(shotImage.image_path),
        title: `镜头 ${shot.shot_id}`,
        subtitle: shot.narration_text || shot.subtitle_text || "当前镜头暂无文案。",
        provider: `${shotImage.provider_name}${shotImage.used_fallback ? " / fallback" : ""}`,
        duration: formatDuration(shot.shot_duration),
        aspectRatio,
      };
    }
  }

  return {
    kind: "placeholder",
    title: "当前模式下还没有预览素材",
    subtitle: "可以先在第二步生成镜头图，或者切到其他预览模式。",
    provider: "等待素材",
    duration: "--",
    aspectRatio,
  };
}

export function buildArtifactEntries(project, assetLinks) {
  if (!project) return [];

  return [
    ["summary.json", normalizeRuntimeUrl(project.artifacts?.summary_path)],
    ["script.json", normalizeRuntimeUrl(project.artifacts?.script_path)],
    ["storyboard.json", normalizeRuntimeUrl(project.artifacts?.storyboard_path)],
    ["news_plan.json", normalizeRuntimeUrl(project.artifacts?.news_plan_path)],
    ["run_report.json", normalizeRuntimeUrl(project.artifacts?.news_report_path)],
    ["selected_sources.md", normalizeRuntimeUrl(project.artifacts?.selected_sources_path)],
    ["音频", assetLinks?.audio_url],
    ["字幕", assetLinks?.subtitle_url],
    ["发布包", assetLinks?.publish_payload_url],
  ].filter((item) => item[1]);
}

export function buildMediaItems(project, assetLinks) {
  if (!project) return [];

  const cards = [];
  if (assetLinks?.final_video_url) {
    cards.push({ kind: "video", title: "最终成片", url: assetLinks.final_video_url, meta: "" });
  }
  if (assetLinks?.preview_video_url) {
    cards.push({ kind: "video", title: "RPA 预览 MP4", url: assetLinks.preview_video_url, meta: "" });
  }
  if (assetLinks?.preview_gif_url) {
    cards.push({ kind: "image", title: "RPA 预览 GIF", url: assetLinks.preview_gif_url, meta: "" });
  }
  if (assetLinks?.preview_cover_url) {
    cards.push({ kind: "image", title: "RPA 封面", url: assetLinks.preview_cover_url, meta: "" });
  }

  (project.artifacts?.shot_images || []).slice(0, 10).forEach((item) => {
    cards.push({
      kind: "image",
      title: `镜头图 ${item.shot_id}`,
      url: normalizeRuntimeUrl(item.image_path),
      meta: `${item.provider_name}${item.used_fallback ? " / fallback" : ""}`,
    });
  });

  (project.artifacts?.shot_videos || []).slice(0, 8).forEach((item) => {
    cards.push({
      kind: "video",
      title: `镜头视频 ${item.shot_id}`,
      url: normalizeRuntimeUrl(item.video_path),
      meta: `${item.provider_name}${item.used_fallback ? " / fallback" : ""}`,
    });
  });

  return cards.filter((item) => item.url);
}
