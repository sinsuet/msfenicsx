from __future__ import annotations

import json
from pathlib import Path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_history_dashboard_html(path: Path, *, history_summary: dict) -> None:
    ensure_parent(path)
    summary_json = json.dumps(history_summary, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Thermal Optimization History Workspace</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: rgba(255,255,255,0.94);
      --line: #d9d0c2;
      --ink: #201c18;
      --muted: #6b635c;
      --accent: #a44a3f;
      --accent-soft: #f5d8d2;
      --good: #2f7a4a;
      --warn: #b66b0d;
      --bad: #a61b1b;
      --shadow: 0 12px 38px rgba(67, 48, 31, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7ed 0, transparent 28rem),
        linear-gradient(180deg, #fbf5ec 0%, var(--bg) 100%);
      font-family: "Segoe UI", "PingFang SC", sans-serif;
    }}
    .shell {{
      max-width: 1540px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{
      margin: 0;
    }}
    .subtitle {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat, .card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
      background: white;
    }}
    .stat-label {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 0.82rem;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 1.22rem;
      font-weight: 700;
    }}
    .layout-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .workspace {{
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.95fr);
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      padding: 18px;
    }}
    .section-title {{
      margin-bottom: 12px;
      font-size: 1.12rem;
    }}
    .chart-grid {{
      display: grid;
      gap: 14px;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .timeline-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    .timeline-table th, .timeline-table td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
      font-size: 0.95rem;
    }}
    .timeline-row {{
      cursor: pointer;
    }}
    .timeline-row.active {{
      background: var(--accent-soft);
    }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .good {{ background: #dbf0df; color: var(--good); }}
    .warn {{ background: #fde9c9; color: var(--warn); }}
    .bad {{ background: #f8d7d7; color: var(--bad); }}
    .muted {{
      color: var(--muted);
    }}
    .detail-grid {{
      display: grid;
      gap: 12px;
    }}
    .detail-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: white;
    }}
    .detail-card pre {{
      white-space: pre-wrap;
      word-break: break-word;
      margin: 8px 0 0;
      font-size: 0.92rem;
      line-height: 1.6;
      font-family: "Cascadia Code", "Consolas", monospace;
    }}
    .iframe-shell {{
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      background: white;
      min-height: 320px;
    }}
    iframe {{
      width: 100%;
      height: 320px;
      border: 0;
      background: white;
    }}
    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
    }}
    .link-row a {{
      display: inline-block;
      text-decoration: none;
      color: white;
      background: var(--accent);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.9rem;
    }}
    @media (max-width: 1180px) {{
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .layout-grid {{ grid-template-columns: 1fr; }}
      .workspace {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Thermal Optimization History Workspace</h1>
      <p class="subtitle">
        这个工作台把初始布局、每轮 LLM 的判断理由、执行动作、验证结果，以及动作在下一轮观察到的真实效果串到同一页里。
        顶部三个窗口分别展示初始布局、当前轮仿真、以及下一轮观察到的效果。
      </p>
      <div class="stats" id="stats"></div>
      <div class="layout-grid">
        <div class="card">
          <h3>Initial Layout</h3>
          <p class="muted">固定展示本组第一轮的布局/温度总览。</p>
          <div class="iframe-shell"><iframe id="initial-overview" title="Initial overview"></iframe></div>
        </div>
        <div class="card">
          <h3>Selected Run</h3>
          <p class="muted">当前选中轮次的仿真总览，也就是 LLM 做决策时面对的状态。</p>
          <div class="iframe-shell"><iframe id="selected-overview" title="Selected run overview"></iframe></div>
        </div>
        <div class="card">
          <h3>Observed Effect</h3>
          <p class="muted">动作的真实效果通常要到下一轮 evaluation 才能观察到。</p>
          <div class="iframe-shell"><iframe id="effect-overview" title="Observed effect overview"></iframe></div>
        </div>
      </div>
    </section>

    <section class="workspace">
      <div class="panel">
        <h2 class="section-title">Timeline And Metrics</h2>
        <div class="chart-grid">
          <div class="card">
            <h3>Chip Peak Temperature By Run</h3>
            <svg id="chip-chart" viewBox="0 0 760 240" aria-label="chip max chart"></svg>
          </div>
          <div class="card">
            <h3>Observed Delta After Each Action</h3>
            <svg id="delta-chart" viewBox="0 0 760 240" aria-label="delta chart"></svg>
          </div>
        </div>
        <table class="timeline-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>Before</th>
              <th>After</th>
              <th>Delta</th>
              <th>Categories</th>
            </tr>
          </thead>
          <tbody id="timeline-body"></tbody>
        </table>
      </div>

      <aside class="panel">
        <h2 class="section-title">Run Detail</h2>
        <div class="detail-grid">
          <div class="detail-card">
            <strong>Summary</strong>
            <pre id="detail-summary"></pre>
          </div>
          <div class="detail-card">
            <strong>Why LLM Chose This</strong>
            <pre id="detail-reason"></pre>
          </div>
          <div class="detail-card">
            <strong>Executed Actions</strong>
            <pre id="detail-actions"></pre>
          </div>
          <div class="detail-card">
            <strong>Expected Vs Actual Effect</strong>
            <pre id="detail-effects"></pre>
          </div>
          <div class="detail-card">
            <strong>Validation And Risks</strong>
            <pre id="detail-validation"></pre>
          </div>
          <div class="detail-card">
            <strong>State Before / After</strong>
            <pre id="detail-state"></pre>
            <div class="link-row" id="detail-links"></div>
          </div>
        </div>
      </aside>
    </section>
  </div>

  <script>
    const historySummary = {summary_json};
    const runs = historySummary.runs || [];

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function formatNumber(value) {{
      return typeof value === "number" ? value.toFixed(6) : "N/A";
    }}

    function formatDelta(value) {{
      return typeof value === "number" ? (value > 0 ? "+" : "") + value.toFixed(6) : "N/A";
    }}

    function statusBadge(status) {{
      if (status === "feasible" || status === "proposal_applied") return '<span class="badge good">' + escapeHtml(status) + '</span>';
      if (status === "invalid_proposal") return '<span class="badge bad">' + escapeHtml(status) + '</span>';
      return '<span class="badge warn">' + escapeHtml(status || "incomplete") + '</span>';
    }}

    function createStats() {{
      const bestRun = runs.reduce((best, run) => {{
        if (typeof run.chip_max_before !== "number") return best;
        if (!best || run.chip_max_before < best.chip_max_before) return run;
        return best;
      }}, null);
      const invalidCount = runs.filter((run) => run.validation_status === "invalid").length;
      const firstFeasible = runs.find((run) => run.feasible === true);
      const latestObserved = [...runs].reverse().find((run) => typeof run.chip_max_before === "number");
      const modelName = runs.find((run) => run.model_info && run.model_info.model)?.model_info?.model || "N/A";
      const items = [
        ["Run Count", historySummary.run_count ?? runs.length],
        ["Latest Observed", latestObserved ? formatNumber(latestObserved.chip_max_before) : "N/A"],
        ["Best Run", bestRun ? bestRun.run_id + " / " + formatNumber(bestRun.chip_max_before) : "N/A"],
        ["First Feasible", firstFeasible ? firstFeasible.run_id : "N/A"],
        ["Invalid Proposals", invalidCount],
        ["Model", modelName],
      ];
      document.getElementById("stats").innerHTML = items.map(([label, value]) => `
        <div class="stat">
          <div class="stat-label">${{escapeHtml(label)}}</div>
          <div class="stat-value">${{escapeHtml(value)}}</div>
        </div>
      `).join("");
    }}

    function renderLineChart(targetId, values, color) {{
      const svg = document.getElementById(targetId);
      const width = 760;
      const height = 240;
      const padding = 36;
      const numeric = values.filter((value) => typeof value === "number");
      if (!numeric.length) {{
        svg.innerHTML = "";
        return;
      }}
      const min = Math.min(...numeric);
      const max = Math.max(...numeric);
      const span = max - min || 1.0;
      const points = values.map((value, index) => {{
        const x = padding + (index * (width - 2 * padding) / Math.max(values.length - 1, 1));
        const y = typeof value === "number"
          ? height - padding - ((value - min) / span) * (height - 2 * padding)
          : height - padding;
        return `${{x}},${{y}}`;
      }}).join(" ");
      let circles = "";
      values.forEach((value, index) => {{
        if (typeof value !== "number") return;
        const x = padding + (index * (width - 2 * padding) / Math.max(values.length - 1, 1));
        const y = height - padding - ((value - min) / span) * (height - 2 * padding);
        circles += `<circle cx="${{x}}" cy="${{y}}" r="4.5" fill="${{color}}"></circle>`;
      }});
      svg.innerHTML = `
        <rect x="0" y="0" width="${{width}}" height="${{height}}" fill="#fff" stroke="#d9d0c2" rx="18"></rect>
        <line x1="${{padding}}" y1="${{height - padding}}" x2="${{width - padding}}" y2="${{height - padding}}" stroke="#b8ab99"></line>
        <line x1="${{padding}}" y1="${{padding}}" x2="${{padding}}" y2="${{height - padding}}" stroke="#b8ab99"></line>
        <polyline fill="none" stroke="${{color}}" stroke-width="3" points="${{points}}"></polyline>
        ${{circles}}
      `;
    }}

    function renderDeltaChart(values) {{
      const svg = document.getElementById("delta-chart");
      const width = 760;
      const height = 240;
      const padding = 36;
      const numeric = values.map((value) => typeof value === "number" ? value : 0);
      const maxAbs = Math.max(...numeric.map((value) => Math.abs(value)), 1);
      const baseline = height / 2;
      const barWidth = Math.max(16, Math.floor((width - 2 * padding) / Math.max(values.length * 1.7, 1)));
      let bars = `
        <rect x="0" y="0" width="${{width}}" height="${{height}}" fill="#fff" stroke="#d9d0c2" rx="18"></rect>
        <line x1="${{padding}}" y1="${{baseline}}" x2="${{width - padding}}" y2="${{baseline}}" stroke="#777"></line>
      `;
      numeric.forEach((value, index) => {{
        const x = padding + index * ((width - 2 * padding) / Math.max(values.length, 1)) + 8;
        const barHeight = Math.abs(value) / maxAbs * (height / 2 - padding);
        const y = value <= 0 ? baseline - barHeight : baseline;
        const fill = value <= 0 ? "#2a9d8f" : "#e76f51";
        bars += `<rect x="${{x}}" y="${{y}}" width="${{barWidth}}" height="${{barHeight}}" fill="${{fill}}" rx="6"></rect>`;
      }});
      svg.innerHTML = bars;
    }}

    function summarizeState(state) {{
      if (!state) return "N/A";
      const components = (state.components || []).map((component) => {{
        const head = `${{component.name}}: (${{component.x0 ?? "?"}}, ${{component.y0 ?? "?"}}) / ${{component.width ?? "?"}} x ${{component.height ?? "?"}}`;
        const material = component.material ? `, material=${{component.material}}` : "";
        const conductivity = typeof component.conductivity === "number" ? `, k=${{component.conductivity}}` : "";
        return head + material + conductivity;
      }});
      return components.length ? components.join("\\n") : "N/A";
    }}

    function summarizeActions(run) {{
      const changes = run.changes || [];
      if (!changes.length) return "No applied changes.";
      return changes.map((change, index) => {{
        const oldValue = change.old ?? "N/A";
        const newValue = change.new ?? "N/A";
        const action = change.action || "set";
        const reason = change.reason ? `\\n   reason: ${{change.reason}}` : "";
        return `${{index + 1}}. ${{change.path || "unknown"}}\\n   action: ${{action}}\\n   old -> new: ${{oldValue}} -> ${{newValue}}${{reason}}`;
      }}).join("\\n\\n");
    }}

    function summarizeEffects(run) {{
      const expected = (run.expected_effects || []).length ? (run.expected_effects || []).map((item, index) => `${{index + 1}}. ${{item}}`).join("\\n") : "No expected effects recorded.";
      const risks = (run.risk_notes || []).length ? (run.risk_notes || []).map((item, index) => `${{index + 1}}. ${{item}}`).join("\\n") : "No risk notes.";
      return [
        "Expected:",
        expected,
        "",
        "Observed:",
        `effect observed in: ${{run.effect_observed_in_run || "N/A"}}`,
        `chip max before: ${{formatNumber(run.chip_max_before)}}`,
        `chip max after: ${{formatNumber(run.chip_max_after)}}`,
        `delta: ${{formatDelta(run.delta_chip_max)}}`,
        "",
        "Risks:",
        risks,
      ].join("\\n");
    }}

    function summarizeValidation(run) {{
      const reasons = (run.validation_reasons || []).length ? (run.validation_reasons || []).map((item, index) => `${{index + 1}}. ${{item}}`).join("\\n") : "No validation blockers.";
      const priorityActions = (run.priority_actions || []).length ? run.priority_actions.map((item, index) => `${{index + 1}}. ${{item}}`).join("\\n") : "N/A";
      return [
        `validation_status: ${{run.validation_status || "unknown"}}`,
        `validation_valid: ${{run.validation_valid}}`,
        `feasible: ${{run.feasible}}`,
        "",
        "Reasons:",
        reasons,
        "",
        "Priority actions:",
        priorityActions,
      ].join("\\n");
    }}

    function renderTimeline() {{
      const tbody = document.getElementById("timeline-body");
      const activeIndex = Math.max(runs.length - 1, 0);
      tbody.innerHTML = runs.map((run, index) => `
        <tr class="timeline-row ${{index === activeIndex ? "active" : ""}}" data-index="${{index}}">
          <td>${{escapeHtml(run.run_id)}}</td>
          <td>${{statusBadge(run.status)}}</td>
          <td>${{formatNumber(run.chip_max_before)}}</td>
          <td>${{formatNumber(run.chip_max_after)}}</td>
          <td>${{formatDelta(run.delta_chip_max)}}</td>
          <td>${{escapeHtml((run.change_categories || []).join(", ") || "-")}}</td>
        </tr>
      `).join("");
      tbody.querySelectorAll(".timeline-row").forEach((row) => {{
        row.addEventListener("click", () => {{
          tbody.querySelectorAll(".timeline-row").forEach((item) => item.classList.remove("active"));
          row.classList.add("active");
          renderDetail(Number(row.dataset.index));
        }});
      }});
    }}

    function renderDetail(index) {{
      const run = runs[index];
      if (!run) return;
      document.getElementById("detail-summary").textContent = [
        `run_id: ${{run.run_id}}`,
        `iteration: ${{run.iteration ?? "N/A"}}`,
        `status: ${{run.status ?? "N/A"}}`,
        `constraint_limit: ${{formatNumber(run.constraint_limit)}}`,
        `chip_max_before: ${{formatNumber(run.chip_max_before)}}`,
        `chip_max_after: ${{formatNumber(run.chip_max_after)}}`,
        `delta_chip_max: ${{formatDelta(run.delta_chip_max)}}`,
        `change_categories: ${{(run.change_categories || []).join(", ") || "-"}}`,
      ].join("\\n");
      document.getElementById("detail-reason").textContent = run.decision_summary || "No decision summary recorded.";
      document.getElementById("detail-actions").textContent = summarizeActions(run);
      document.getElementById("detail-effects").textContent = summarizeEffects(run);
      document.getElementById("detail-validation").textContent = summarizeValidation(run);
      document.getElementById("detail-state").textContent = [
        "Before:",
        summarizeState(run.state_snapshot),
        "",
        "After:",
        summarizeState(run.next_state_snapshot),
      ].join("\\n");

      document.getElementById("selected-overview").src = run.overview_html || "";
      document.getElementById("effect-overview").src = run.next_overview_html || run.overview_html || "";

      const links = [];
      if (run.overview_html) links.push(`<a href="${{escapeHtml(run.overview_html)}}">Open Current Overview</a>`);
      if (run.temperature_html) links.push(`<a href="${{escapeHtml(run.temperature_html)}}">Open Current Temperature</a>`);
      if (run.next_overview_html) links.push(`<a href="${{escapeHtml(run.next_overview_html)}}">Open Observed Effect</a>`);
      if (run.state_path) links.push(`<a href="${{escapeHtml(run.state_path)}}">Open state.yaml</a>`);
      if (run.next_state_path) links.push(`<a href="${{escapeHtml(run.next_state_path)}}">Open next_state.yaml</a>`);
      document.getElementById("detail-links").innerHTML = links.join("");
    }}

    createStats();
    document.getElementById("initial-overview").src = historySummary.initial_overview_html || "";
    renderLineChart("chip-chart", runs.map((run) => run.chip_max_before), "#a44a3f");
    renderDeltaChart(runs.map((run) => run.delta_chip_max));
    renderTimeline();
    renderDetail(Math.max(runs.length - 1, 0));
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def save_history_collection_html(path: Path, *, collection_summary: dict) -> None:
    ensure_parent(path)
    summary_json = json.dumps(collection_summary, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Thermal Optimization History Collection</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: rgba(255,255,255,0.94);
      --line: #d9d0c2;
      --ink: #201c18;
      --muted: #6b635c;
      --accent: #a44a3f;
      --shadow: 0 12px 38px rgba(67, 48, 31, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7ed 0, transparent 28rem),
        linear-gradient(180deg, #fbf5ec 0%, var(--bg) 100%);
      font-family: "Segoe UI", "PingFang SC", sans-serif;
    }}
    .shell {{
      max-width: 1540px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 18px;
    }}
    .subtitle {{
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat, .figure-card, .group-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
      background: white;
    }}
    .stat-label {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 0.82rem;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 1.22rem;
      font-weight: 700;
    }}
    .panel {{
      padding: 18px;
    }}
    .figure-grid, .group-grid {{
      display: grid;
      gap: 14px;
    }}
    .figure-grid {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-bottom: 18px;
    }}
    .group-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .meta {{
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.94rem;
      margin-top: 8px;
    }}
    a.button {{
      display: inline-block;
      margin-top: 12px;
      text-decoration: none;
      color: white;
      background: var(--accent);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.9rem;
    }}
    @media (max-width: 1180px) {{
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .figure-grid, .group-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Thermal Optimization History Collection</h1>
      <p class="subtitle">
        这个总览页面面向批量实验目录。上半部分给出跨组统计和已有聚合图，下半部分给出每组入口，方便你跳到任一组的详细历史工作台。
      </p>
      <div class="stats" id="stats"></div>
    </section>

    <section class="panel">
      <h2>Aggregate Figures</h2>
      <div class="figure-grid" id="figure-grid"></div>
      <h2>Group Dashboards</h2>
      <div class="group-grid" id="group-grid"></div>
    </section>
  </div>

  <script>
    const collectionSummary = {summary_json};
    const groups = collectionSummary.groups || [];

    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function formatNumber(value) {{
      return typeof value === "number" ? value.toFixed(6) : "N/A";
    }}

    function renderStats() {{
      const items = [
        ["Group Count", collectionSummary.group_count ?? groups.length],
        ["Feasible Groups", collectionSummary.feasible_group_count ?? "N/A"],
        ["Average Latest", formatNumber(collectionSummary.average_latest_chip_max)],
        ["Best Group", collectionSummary.best_group_id || "N/A"],
        ["Best Chip Max", formatNumber(collectionSummary.best_group_chip_max)],
      ];
      document.getElementById("stats").innerHTML = items.map(([label, value]) => `
        <div class="stat">
          <div class="stat-label">${{escapeHtml(label)}}</div>
          <div class="stat-value">${{escapeHtml(value)}}</div>
        </div>
      `).join("");
    }}

    function renderFigures() {{
      const labels = {{
        trajectories: "Trajectories",
        final_chip_max: "Final Chip Max",
        first_base_k_round: "First Base K Round",
      }};
      const figures = collectionSummary.aggregate_figures || {{}};
      document.getElementById("figure-grid").innerHTML = Object.entries(figures)
        .filter(([, value]) => Boolean(value))
        .map(([key, value]) => `
          <div class="figure-card">
            <h3>${{escapeHtml(labels[key] || key)}}</h3>
            <img src="${{escapeHtml(value)}}" alt="${{escapeHtml(labels[key] || key)}}">
          </div>
        `)
        .join("") || '<div class="figure-card">No aggregate figures found.</div>';
    }}

    function renderGroups() {{
      document.getElementById("group-grid").innerHTML = groups.map((group) => `
        <div class="group-card">
          <h3>${{escapeHtml(group.group_id)}}</h3>
          <div class="meta">
            run_count: ${{escapeHtml(group.run_count)}}<br>
            initial_chip_max: ${{escapeHtml(formatNumber(group.initial_chip_max))}}<br>
            latest_observed_chip_max: ${{escapeHtml(formatNumber(group.latest_observed_chip_max))}}<br>
            best_chip_max: ${{escapeHtml(formatNumber(group.best_chip_max))}}<br>
            first_feasible_run: ${{escapeHtml(group.first_feasible_run || "N/A")}}<br>
            first_base_k_run: ${{escapeHtml(group.first_base_k_run || "N/A")}}<br>
            invalid_run_count: ${{escapeHtml(group.invalid_run_count)}}<br>
            latest_status: ${{escapeHtml(group.latest_status || "N/A")}}
          </div>
          <a class="button" href="${{escapeHtml(group.history_html || '#')}}">Open Group Dashboard</a>
        </div>
      `).join("");
    }}

    renderStats();
    renderFigures();
    renderGroups();
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
