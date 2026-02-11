"""
dashboard.py — 将所有图表组装为完整的 HTML 仪表板。

核心功能:
  - CSS Grid 布局 (科技蓝主题)
  - KPI 指标卡片 (纯 HTML)
  - 嵌入所有 pyecharts 图表
  - 开发者点击事件 -> 个人面板 (弹窗)
  - 时间维度选择器 (JS 联动)
"""
from __future__ import annotations

import json
import os
import datetime
from typing import Any, Dict

import pandas as pd
from pyecharts.render import engine as pyecharts_engine

from charts import (
    build_calendar_heatmap,
    build_personnel_trend_chart,
    build_activity_sunburst,
    build_lifecycle_scatter,
    build_commit_rank_bar,
    build_night_commit_rank,
    build_maintenance_rank,
    build_code_activity_chart,
    build_file_heatmap_sunburst,
    build_code_stability_chart,
    build_developer_detail_charts,
)


def _chart_to_html_fragment(chart) -> str:
    """将 pyecharts 图表对象转为可嵌入的 HTML 片段 (不含 <html>/<body>)。"""
    # 使用 render_embed 获取 JS 代码，或回退到 render_notebook_html
    try:
        return chart.render_notebook().data
    except Exception:
        pass
    # 回退: 渲染到临时文件再读取 body
    import tempfile
    tmp = tempfile.mktemp(suffix=".html")
    try:
        chart.render(tmp)
        with open(tmp, "r", encoding="utf-8") as f:
            html = f.read()
        # 提取 body 内容
        start = html.find("<body>")
        end = html.find("</body>")
        if start != -1 and end != -1:
            return html[start + 6 : end]
        return html
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _render_chart_div(chart, div_id: str) -> str:
    """将 pyecharts 图表渲染为独立的 div + script 片段。"""
    import tempfile
    tmp = tempfile.mktemp(suffix=".html")
    try:
        chart.render(tmp)
        with open(tmp, "r", encoding="utf-8") as f:
            full_html = f.read()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    # 提取 <script> 内容和图表 <div>
    # pyecharts 生成的 HTML 结构:
    #   <div id="xxx" ...></div>
    #   <script> ... </script>
    import re

    # 找所有 <div id="..."> 和 <script> 块
    divs = re.findall(r'(<div id="[^"]*"[^>]*></div>)', full_html)
    scripts = re.findall(r'(<script>.*?</script>)', full_html, re.DOTALL)

    # 排除 echarts.min.js 的加载脚本
    chart_scripts = [s for s in scripts if "echarts.min.js" not in s and "var chart_" in s]

    fragment = "\n".join(divs) + "\n" + "\n".join(chart_scripts)
    return fragment


def _build_kpi_cards_html(metrics: Dict[str, Any]) -> str:
    """构建 KPI 指标卡片 HTML。"""
    cards = [
        ("📊", "总提交数", f"{metrics.get('total_commits', 0):,}"),
        ("👥", "总开发者", f"{metrics.get('total_authors', 0)}"),
        ("🟢", "活跃开发者", f"{metrics.get('active_authors_6m', 0)}"),
        ("📈", "代码净增长", f"{metrics.get('net_lines', 0):+,} 行"),
        ("📅", "项目生命周期", f"{metrics.get('project_lifecycle_days', 0):,} 天"),
    ]

    html = '<div class="kpi-grid">\n'
    for icon, label, value in cards:
        html += f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>"""
    html += "\n</div>"
    return html


def _build_developer_panels_js(
    prepared_df: pd.DataFrame,
    author_stats: pd.DataFrame,
) -> str:
    """
    预计算所有开发者的详情数据，生成 JS 对象供弹窗使用。
    """
    if author_stats.empty:
        return "var devData = {};"

    dev_data = {}
    for author_name in author_stats.index:
        detail = build_developer_detail_charts(prepared_df, str(author_name), author_stats)
        if not detail:
            continue
        info = detail.get("info", {})
        dev_data[str(author_name)] = info

    # 序列化为 JS
    return f"var devData = {json.dumps(dev_data, ensure_ascii=False, default=str)};"


def build_dashboard_html(
    metrics: Dict[str, Any],
    repo_name: str,
    output_file: str,
) -> str:
    """将所有指标和图表组装为完整的 HTML 仪表板。"""

    # ---- 构建所有图表 ----
    daily_commits = metrics.get("daily_commits", pd.Series(dtype=int))
    monthly_trends = metrics.get("monthly_trends", pd.DataFrame())
    author_stats = metrics.get("author_stats", pd.DataFrame())
    code_activity = metrics.get("code_activity", pd.DataFrame())
    code_stability = metrics.get("code_stability", pd.DataFrame())
    file_heatmap = metrics.get("file_heatmap", [])
    prepared_df = metrics.get("prepared_df", pd.DataFrame())

    charts_html_list = []

    # 各图表渲染
    chart_builders = [
        ("calendar", build_calendar_heatmap, (daily_commits,)),
        ("trend", build_personnel_trend_chart, (monthly_trends,)),
        ("sunburst", build_activity_sunburst, (author_stats,)),
        ("scatter", build_lifecycle_scatter, (author_stats,)),
        ("commit_rank", build_commit_rank_bar, (author_stats,)),
        ("night_rank", build_night_commit_rank, (author_stats,)),
        ("maint_rank", build_maintenance_rank, (author_stats,)),
        ("code_activity", build_code_activity_chart, (code_activity,)),
        ("file_heat", build_file_heatmap_sunburst, (file_heatmap,)),
        ("code_stability", build_code_stability_chart, (code_stability,)),
    ]

    chart_fragments: Dict[str, str] = {}
    for chart_id, builder, args in chart_builders:
        try:
            chart_obj = builder(*args)
            fragment = _render_chart_div(chart_obj, chart_id)
            chart_fragments[chart_id] = fragment
        except Exception as e:
            chart_fragments[chart_id] = f'<div class="chart-error">图表 {chart_id} 渲染失败: {e}</div>'

    # Developer detail radar charts (pre-render top 20)
    dev_radar_fragments: Dict[str, str] = {}
    dev_calendar_fragments: Dict[str, str] = {}
    if not author_stats.empty and not prepared_df.empty:
        top_authors = list(author_stats.index[:20])
        for author_name in top_authors:
            try:
                detail = build_developer_detail_charts(prepared_df, str(author_name), author_stats)
                if detail and detail.get("radar"):
                    dev_radar_fragments[str(author_name)] = _render_chart_div(detail["radar"], f"radar_{author_name}")
                if detail and detail.get("calendar"):
                    dev_calendar_fragments[str(author_name)] = _render_chart_div(detail["calendar"], f"cal_{author_name}")
            except Exception:
                pass

    # Developer data JS
    dev_data_js = _build_developer_panels_js(prepared_df, author_stats)

    # Developer fragments JS map
    dev_radar_js_map = json.dumps(
        {k: v for k, v in dev_radar_fragments.items()},
        ensure_ascii=False,
    )
    dev_calendar_js_map = json.dumps(
        {k: v for k, v in dev_calendar_fragments.items()},
        ensure_ascii=False,
    )

    # ---- KPI ----
    kpi_html = _build_kpi_cards_html(metrics)

    # ---- 分析时间 ----
    analysis_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    date_range = metrics.get("date_range", "")

    # ---- 组装完整 HTML ----
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Git 项目人员分析 — {repo_name}</title>
<script src="https://assets.pyecharts.org/assets/v5/echarts.min.js"></script>
<style>
  :root {{
    --bg-primary: #0f1724;
    --bg-secondary: #1a2332;
    --bg-card: #1e2a3a;
    --bg-card-hover: #243447;
    --accent: #3b82f6;
    --accent-light: #60a5fa;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #2d3f52;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --purple: #8b5cf6;
    --gradient-blue: linear-gradient(135deg, #1e3a5f 0%, #0f1724 100%);
    --shadow: 0 4px 24px rgba(0,0,0,0.3);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
  }}
  .dashboard-header {{
    background: var(--gradient-blue);
    padding: 28px 40px 20px;
    border-bottom: 1px solid var(--border);
  }}
  .dashboard-header h1 {{
    font-size: 28px;
    font-weight: 700;
    color: var(--accent-light);
    margin-bottom: 6px;
  }}
  .dashboard-header .meta {{
    color: var(--text-secondary);
    font-size: 14px;
  }}

  /* KPI Grid */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    padding: 20px 40px;
  }}
  .kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .kpi-card:hover {{
    transform: translateY(-3px);
    box-shadow: var(--shadow);
    border-color: var(--accent);
  }}
  .kpi-icon {{ font-size: 28px; margin-bottom: 8px; }}
  .kpi-value {{
    font-size: 26px;
    font-weight: 700;
    color: var(--accent-light);
    margin-bottom: 4px;
  }}
  .kpi-label {{ font-size: 13px; color: var(--text-secondary); }}

  /* Layout Grid */
  .dashboard-body {{ padding: 0 40px 40px; }}
  .section-title {{
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 28px 0 14px;
    padding-left: 12px;
    border-left: 3px solid var(--accent);
  }}
  .chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }}
  .chart-grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
  }}
  .chart-panel {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    overflow: hidden;
  }}
  .chart-panel.full-width {{
    grid-column: 1 / -1;
  }}
  .chart-error {{
    color: var(--danger);
    padding: 20px;
    text-align: center;
  }}

  /* Developer Modal */
  .modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 1000;
    justify-content: center;
    align-items: center;
  }}
  .modal-overlay.active {{ display: flex; }}
  .modal-content {{
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 30px;
    width: 90%;
    max-width: 1100px;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  }}
  .modal-close {{
    float: right;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 24px;
    cursor: pointer;
    padding: 4px 12px;
    border-radius: 8px;
  }}
  .modal-close:hover {{ background: var(--bg-card); color: var(--text-primary); }}
  .dev-info-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 20px 0;
  }}
  .dev-info-item {{
    background: var(--bg-card);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }}
  .dev-info-item .val {{
    font-size: 20px;
    font-weight: 700;
    color: var(--accent-light);
  }}
  .dev-info-item .lbl {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
  }}
  .dev-charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
  }}
  .dev-chart-box {{
    background: var(--bg-card);
    border-radius: 8px;
    padding: 12px;
    min-height: 320px;
  }}
  .status-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }}
  .status-active {{ background: #16452680; color: var(--success); }}
  .status-inactive {{ background: #3f3f4640; color: var(--text-muted); }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 8px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg-primary); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}

  /* Footer */
  .dashboard-footer {{
    text-align: center;
    padding: 20px;
    color: var(--text-muted);
    font-size: 13px;
    border-top: 1px solid var(--border);
  }}

  /* Responsive */
  @media (max-width: 1200px) {{
    .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
    .chart-grid {{ grid-template-columns: 1fr; }}
    .chart-grid-3 {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="dashboard-header">
  <h1>📊 {repo_name} — 项目人员分析报告</h1>
  <div class="meta">分析时间: {analysis_time} | 数据范围: {date_range}</div>
</div>

<!-- KPI Cards -->
{kpi_html}

<div class="dashboard-body">

  <!-- Calendar Section -->
  <div class="section-title">提交活动日历</div>
  <div class="chart-panel full-width">
    {chart_fragments.get("calendar", "")}
  </div>

  <!-- Personnel Analysis Section -->
  <div class="section-title">人员分析</div>
  <div class="chart-grid">
    <div class="chart-panel">
      {chart_fragments.get("trend", "")}
    </div>
    <div class="chart-panel">
      {chart_fragments.get("sunburst", "")}
    </div>
  </div>

  <div class="chart-panel" style="margin-top:20px;">
    {chart_fragments.get("scatter", "")}
  </div>

  <!-- Ranking Section -->
  <div class="section-title">开发者排行榜</div>
  <div class="chart-grid-3">
    <div class="chart-panel">
      {chart_fragments.get("commit_rank", "")}
    </div>
    <div class="chart-panel">
      {chart_fragments.get("night_rank", "")}
    </div>
    <div class="chart-panel">
      {chart_fragments.get("maint_rank", "")}
    </div>
  </div>

  <!-- Code Analysis Section -->
  <div class="section-title">代码库分析</div>
  <div class="chart-grid">
    <div class="chart-panel">
      {chart_fragments.get("code_activity", "")}
    </div>
    <div class="chart-panel">
      {chart_fragments.get("code_stability", "")}
    </div>
  </div>

  <!-- File Analysis Section -->
  <div class="section-title">文件修改热度</div>
  <div class="chart-panel full-width">
    {chart_fragments.get("file_heat", "")}
  </div>

</div>

<!-- Developer Detail Modal -->
<div class="modal-overlay" id="devModal">
  <div class="modal-content">
    <button class="modal-close" onclick="closeDevModal()">&times;</button>
    <h2 id="devModalTitle" style="font-size:22px;margin-bottom:4px;"></h2>
    <div id="devModalBadge"></div>
    <div class="dev-info-grid" id="devInfoGrid"></div>
    <div class="dev-charts-grid">
      <div class="dev-chart-box" id="devRadarBox"></div>
      <div class="dev-chart-box" id="devCalendarBox"></div>
    </div>
  </div>
</div>

<!-- Footer -->
<div class="dashboard-footer">
  Git 项目人员分析可视化系统 · GitEinsicht · 由 pyecharts 驱动
</div>

<script>
// Developer data
{dev_data_js}
var devRadarFragments = {dev_radar_js_map};
var devCalendarFragments = {dev_calendar_js_map};

function showDevModal(name) {{
  var d = devData[name];
  if (!d) {{ alert('未找到开发者: ' + name); return; }}

  document.getElementById('devModalTitle').textContent = d.name + ' (' + (d.email||'') + ')';

  var badgeClass = d.is_active ? 'status-active' : 'status-inactive';
  var badgeText = d.is_active ? '活跃' : '不活跃';
  document.getElementById('devModalBadge').innerHTML =
    '<span class="status-badge ' + badgeClass + '">' + badgeText + '</span>';

  var infoItems = [
    ['首次提交', d.first_commit],
    ['最后提交', d.last_commit],
    ['总提交数', d.total_commits],
    ['新增行数', (d.total_insertions||0).toLocaleString()],
    ['删除行数', (d.total_deletions||0).toLocaleString()],
    ['维护天数', d.maintenance_days + ' 天'],
    ['夜间提交', d.night_commits],
    ['夜间占比', d.night_ratio + '%'],
  ];
  var infoHtml = '';
  for (var i = 0; i < infoItems.length; i++) {{
    infoHtml += '<div class="dev-info-item"><div class="val">' +
      infoItems[i][1] + '</div><div class="lbl">' + infoItems[i][0] + '</div></div>';
  }}
  document.getElementById('devInfoGrid').innerHTML = infoHtml;

  // Radar chart
  var radarBox = document.getElementById('devRadarBox');
  radarBox.innerHTML = devRadarFragments[name] || '<p style="text-align:center;padding:60px;color:#64748b;">暂无雷达图数据</p>';
  // Re-run scripts
  var scripts = radarBox.querySelectorAll('script');
  scripts.forEach(function(s) {{
    var ns = document.createElement('script');
    ns.text = s.text;
    s.parentNode.replaceChild(ns, s);
  }});

  // Calendar chart
  var calBox = document.getElementById('devCalendarBox');
  calBox.innerHTML = devCalendarFragments[name] || '<p style="text-align:center;padding:60px;color:#64748b;">暂无日历数据</p>';
  var scripts2 = calBox.querySelectorAll('script');
  scripts2.forEach(function(s) {{
    var ns = document.createElement('script');
    ns.text = s.text;
    s.parentNode.replaceChild(ns, s);
  }});

  document.getElementById('devModal').classList.add('active');
}}

function closeDevModal() {{
  document.getElementById('devModal').classList.remove('active');
}}

// Close modal on outside click
document.getElementById('devModal').addEventListener('click', function(e) {{
  if (e.target === this) closeDevModal();
}});

// Close on Escape
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeDevModal();
}});

// Hook into echarts instances to capture clicks on developer names
// We use a MutationObserver approach: after all charts render,
// find all echarts instances and attach click handlers.
window.addEventListener('load', function() {{
  setTimeout(function() {{
    // Find all echarts instances
    var containers = document.querySelectorAll('[_echarts_instance_]');
    containers.forEach(function(el) {{
      var chart = echarts.getInstanceByDom(el);
      if (chart) {{
        chart.on('click', function(params) {{
          // Check if clicked on a developer name (bar chart name, scatter point, etc.)
          var name = params.name || (params.value && params.value[3]);
          if (name && devData[name]) {{
            showDevModal(name);
          }}
        }});
      }}
    }});
  }}, 1500);  // Wait for charts to finish rendering
}});
</script>

</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return output_file
