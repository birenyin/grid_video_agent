import { EmptyState, Field } from "./Shared";

function DrawerShell({ open, title, eyebrow, onClose, children }) {
  return (
    <div className={`drawer-shell ${open ? "open" : ""}`}>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-head">
          <div>
            <div className="panel-eyebrow">{eyebrow}</div>
            <h2>{title}</h2>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>
            关闭
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}

export function CreateDrawer({
  open,
  busy,
  createTab,
  createForms,
  onClose,
  onTabChange,
  onFieldChange,
  onSubmit,
}) {
  const tabMeta = [
    { key: "text", label: "正文输入" },
    { key: "script", label: "现成脚本" },
    { key: "url", label: "网页链接" },
    { key: "feed", label: "RPA Feed" },
  ];

  return (
    <DrawerShell open={open} title="新建项目" eyebrow="Create" onClose={onClose}>
      <div className="drawer-tabs">
        {tabMeta.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`ghost-button ${createTab === tab.key ? "active" : ""}`}
            onClick={() => onTabChange(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="drawer-scroll">
        {createTab === "text" ? (
          <div className="form-grid">
            <Field label="标题">
              <input value={createForms.text.title} onChange={(event) => onFieldChange("text", "title", event.target.value)} />
            </Field>
            <Field label="模式">
              <select value={createForms.text.mode} onChange={(event) => onFieldChange("text", "mode", event.target.value)}>
                <option value="news_mode">news_mode</option>
                <option value="explain_mode">explain_mode</option>
              </select>
            </Field>
            <Field label="时长（秒）">
              <input
                type="number"
                min="15"
                max="150"
                value={createForms.text.target_duration_seconds}
                onChange={(event) => onFieldChange("text", "target_duration_seconds", Number(event.target.value))}
              />
            </Field>
            <Field label="画幅">
              <select
                value={createForms.text.aspect_ratio}
                onChange={(event) => onFieldChange("text", "aspect_ratio", event.target.value)}
              >
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
              </select>
            </Field>
            <Field label="来源链接" span>
              <input
                value={createForms.text.source_url}
                onChange={(event) => onFieldChange("text", "source_url", event.target.value)}
              />
            </Field>
            <Field label="正文" span>
              <textarea
                rows="9"
                value={createForms.text.content_text}
                onChange={(event) => onFieldChange("text", "content_text", event.target.value)}
              />
            </Field>
            <button
              type="button"
              className="primary-button wide"
              disabled={busy || !createForms.text.content_text.trim()}
              onClick={() => onSubmit("text", "/projects/create_from_text")}
            >
              生成项目草稿
            </button>
          </div>
        ) : null}

        {createTab === "script" ? (
          <div className="form-grid">
            <Field label="标题">
              <input value={createForms.script.title} onChange={(event) => onFieldChange("script", "title", event.target.value)} />
            </Field>
            <Field label="模式">
              <select
                value={createForms.script.mode}
                onChange={(event) => onFieldChange("script", "mode", event.target.value)}
              >
                <option value="explain_mode">explain_mode</option>
                <option value="news_mode">news_mode</option>
              </select>
            </Field>
            <Field label="时长（秒）">
              <input
                type="number"
                min="15"
                max="150"
                value={createForms.script.target_duration_seconds}
                onChange={(event) => onFieldChange("script", "target_duration_seconds", Number(event.target.value))}
              />
            </Field>
            <Field label="画幅">
              <select
                value={createForms.script.aspect_ratio}
                onChange={(event) => onFieldChange("script", "aspect_ratio", event.target.value)}
              >
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
              </select>
            </Field>
            <Field label="完整脚本" span>
              <textarea
                rows="9"
                value={createForms.script.full_script}
                onChange={(event) => onFieldChange("script", "full_script", event.target.value)}
              />
            </Field>
            <button
              type="button"
              className="primary-button wide"
              disabled={busy || !createForms.script.title.trim() || !createForms.script.full_script.trim()}
              onClick={() => onSubmit("script", "/projects/create_from_script")}
            >
              从脚本创建项目
            </button>
          </div>
        ) : null}

        {createTab === "url" ? (
          <div className="form-grid">
            <Field label="网页链接" span>
              <input
                value={createForms.url.source_url}
                onChange={(event) => onFieldChange("url", "source_url", event.target.value)}
              />
            </Field>
            <Field label="标题">
              <input value={createForms.url.title} onChange={(event) => onFieldChange("url", "title", event.target.value)} />
            </Field>
            <Field label="模式">
              <select value={createForms.url.mode} onChange={(event) => onFieldChange("url", "mode", event.target.value)}>
                <option value="news_mode">news_mode</option>
                <option value="explain_mode">explain_mode</option>
              </select>
            </Field>
            <Field label="时长（秒）">
              <input
                type="number"
                min="15"
                max="150"
                value={createForms.url.target_duration_seconds}
                onChange={(event) => onFieldChange("url", "target_duration_seconds", Number(event.target.value))}
              />
            </Field>
            <Field label="画幅">
              <select
                value={createForms.url.aspect_ratio}
                onChange={(event) => onFieldChange("url", "aspect_ratio", event.target.value)}
              >
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
              </select>
            </Field>
            <button
              type="button"
              className="primary-button wide"
              disabled={busy || !createForms.url.source_url.trim()}
              onClick={() => onSubmit("url", "/projects/create_from_url")}
            >
              抓取网页并建项目
            </button>
          </div>
        ) : null}

        {createTab === "feed" ? (
          <div className="form-grid">
            <Field label="Feed 路径" span>
              <input
                value={createForms.feed.feed_path}
                onChange={(event) => onFieldChange("feed", "feed_path", event.target.value)}
              />
            </Field>
            <Field label="标题">
              <input value={createForms.feed.title} onChange={(event) => onFieldChange("feed", "title", event.target.value)} />
            </Field>
            <Field label="规划模式">
              <select
                value={createForms.feed.plan_mode}
                onChange={(event) => onFieldChange("feed", "plan_mode", event.target.value)}
              >
                <option value="rule">rule</option>
                <option value="auto">auto</option>
                <option value="api">api</option>
              </select>
            </Field>
            <Field label="模式">
              <select value={createForms.feed.mode} onChange={(event) => onFieldChange("feed", "mode", event.target.value)}>
                <option value="news_mode">news_mode</option>
                <option value="explain_mode">explain_mode</option>
              </select>
            </Field>
            <Field label="时长（秒）">
              <input
                type="number"
                min="15"
                max="150"
                value={createForms.feed.target_duration_seconds}
                onChange={(event) => onFieldChange("feed", "target_duration_seconds", Number(event.target.value))}
              />
            </Field>
            <Field label="画幅">
              <select
                value={createForms.feed.aspect_ratio}
                onChange={(event) => onFieldChange("feed", "aspect_ratio", event.target.value)}
              >
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
              </select>
            </Field>
            <label className="checkbox-field span-all">
              <input
                type="checkbox"
                checked={createForms.feed.render_preview_bundle}
                onChange={(event) => onFieldChange("feed", "render_preview_bundle", event.target.checked)}
              />
              先生成 newsroom 预览包
            </label>
            <button
              type="button"
              className="primary-button wide"
              disabled={busy || !createForms.feed.feed_path.trim()}
              onClick={() => onSubmit("feed", "/projects/create_from_rpa_feed")}
            >
              从 RPA Feed 建项目
            </button>
          </div>
        ) : null}
      </div>
    </DrawerShell>
  );
}

export function AutomationDrawer({
  open,
  busy,
  form,
  jobs,
  onClose,
  onFieldChange,
  onSubmit,
  onRunNow,
  onToggleStatus,
}) {
  return (
    <DrawerShell open={open} title="自动抓站与定时任务" eyebrow="Automation" onClose={onClose}>
      <div className="drawer-scroll">
        <div className="panel-card">
          <div className="panel-card-head">
            <div>
              <div className="panel-eyebrow">Create Job</div>
              <h3>新建自动任务</h3>
            </div>
          </div>
          <div className="form-grid">
            <Field label="任务名称">
              <input value={form.name} onChange={(event) => onFieldChange("name", event.target.value)} />
            </Field>
            <Field label="站点集合">
              <select value={form.source_set} onChange={(event) => onFieldChange("source_set", event.target.value)}>
                <option value="mixed">mixed</option>
                <option value="official">official</option>
              </select>
            </Field>
            <Field label="间隔（分钟）">
              <input
                type="number"
                min="5"
                max="10080"
                value={form.interval_minutes}
                onChange={(event) => onFieldChange("interval_minutes", Number(event.target.value))}
              />
            </Field>
            <Field label="规划模式">
              <select value={form.plan_mode} onChange={(event) => onFieldChange("plan_mode", event.target.value)}>
                <option value="rule">rule</option>
                <option value="auto">auto</option>
                <option value="api">api</option>
              </select>
            </Field>
            <Field label="每站抓取上限">
              <input
                type="number"
                min="1"
                max="10"
                value={form.per_source_limit}
                onChange={(event) => onFieldChange("per_source_limit", Number(event.target.value))}
              />
            </Field>
            <Field label="总抓取上限">
              <input
                type="number"
                min="1"
                max="20"
                value={form.total_fetch_limit}
                onChange={(event) => onFieldChange("total_fetch_limit", Number(event.target.value))}
              />
            </Field>
            <Field label="视频模式">
              <select value={form.mode} onChange={(event) => onFieldChange("mode", event.target.value)}>
                <option value="news_mode">news_mode</option>
                <option value="explain_mode">explain_mode</option>
              </select>
            </Field>
            <Field label="时长（秒）">
              <input
                type="number"
                min="15"
                max="150"
                value={form.target_duration_seconds}
                onChange={(event) => onFieldChange("target_duration_seconds", Number(event.target.value))}
              />
            </Field>
            <Field label="画幅">
              <select value={form.aspect_ratio} onChange={(event) => onFieldChange("aspect_ratio", event.target.value)}>
                <option value="9:16">9:16 竖屏</option>
                <option value="16:9">16:9 横屏</option>
              </select>
            </Field>
            <Field label="自动渲染模式">
              <select value={form.render_mode} onChange={(event) => onFieldChange("render_mode", event.target.value)}>
                <option value="image_audio">image_audio</option>
                <option value="video_audio">video_audio</option>
              </select>
            </Field>
            <Field label="配音音色">
              <select value={form.preferred_voice} onChange={(event) => onFieldChange("preferred_voice", event.target.value)}>
                <option value="professional_cn_male">professional_cn_male</option>
                <option value="professional_cn_female">professional_cn_female</option>
                <option value="zh_male_m191_uranus_bigtts">云舟 2.0</option>
                <option value="zh_female_xiaohe_uranus_bigtts">小何 2.0</option>
              </select>
            </Field>
            <Field label="发布模式">
              <select value={form.publish_mode} onChange={(event) => onFieldChange("publish_mode", event.target.value)}>
                <option value="draft">draft</option>
                <option value="direct">direct</option>
              </select>
            </Field>
            <Field label="参考人物图" span>
              <input
                value={form.reference_image_path}
                onChange={(event) => onFieldChange("reference_image_path", event.target.value)}
                placeholder="不填则自动使用默认人物图"
              />
            </Field>
            <label className="checkbox-field span-all">
              <input type="checkbox" checked={form.auto_render} onChange={(event) => onFieldChange("auto_render", event.target.checked)} />
              抓取后自动渲染
            </label>
            <button type="button" className="primary-button wide" disabled={busy || !form.name.trim()} onClick={onSubmit}>
              创建自动任务
            </button>
          </div>
        </div>

        <div className="panel-card">
          <div className="panel-card-head">
            <div>
              <div className="panel-eyebrow">Job List</div>
              <h3>现有任务</h3>
            </div>
          </div>
          {jobs.length ? (
            <div className="automation-job-list">
              {jobs.map((job) => (
                <article key={job.job_id} className="automation-job-card">
                  <div className="automation-job-head">
                    <div>
                      <strong>{job.name}</strong>
                      <p>{job.job_id}</p>
                    </div>
                    <span className={`soft-chip ${job.status === "active" ? "ok" : "warn"}`}>{job.status}</span>
                  </div>
                  <div className="automation-job-meta">
                    <span>{job.fetch.source_set}</span>
                    <span>每 {job.interval_minutes} 分钟</span>
                    <span>{job.mode}</span>
                    <span>{job.render.render_mode}</span>
                  </div>
                  <div className="automation-job-footer">
                    <div className="small-copy">
                      <div>最近运行：{job.last_run_at ? new Date(job.last_run_at).toLocaleString() : "从未运行"}</div>
                      <div>下次运行：{job.next_run_at ? new Date(job.next_run_at).toLocaleString() : "未安排"}</div>
                      {job.last_error ? <div className="danger-copy">错误：{job.last_error}</div> : null}
                    </div>
                    <div className="panel-actions">
                      <button type="button" className="ghost-button" onClick={() => onRunNow(job.job_id)}>
                        Run Now
                      </button>
                      <button
                        type="button"
                        className="ghost-button"
                        onClick={() => onToggleStatus(job.job_id, job.status === "paused" ? "active" : "paused")}
                      >
                        {job.status === "paused" ? "恢复" : "暂停"}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="还没有自动任务" body="创建后就能定时抓电网资讯、自动建项目、自动渲染。" compact />
          )}
        </div>
      </div>
    </DrawerShell>
  );
}
