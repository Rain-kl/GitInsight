"""
charts.py — pyecharts 图表构建器。

包含所有图表的构建函数:
  - 日历热力图
  - 人员变动趋势折线图
  - 开发者活跃状态旭日图
  - 开发者生命周期散点图
  - 提交排行榜 (横向条形图)
  - 卷王榜 (夜间提交排行)
  - 最长维护榜 (分段条形图)
  - 代码活动趋势图 (双Y轴)
  - 文件修改热度旭日图
  - 代码稳定性分析图
  - 开发者个人分析面板 (信息卡 + 时间线 + 热力图 + 雷达图)
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import (
    Bar,
    Calendar,
    Line,
    Page,
    Pie,
    Radar,
    Scatter,
    Sunburst,
    Tab,
    Timeline,
    Grid,
)
from pyecharts.globals import ThemeType
from pyecharts.commons.utils import JsCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_int_list(values) -> List[int]:
    """Convert numpy/pandas integers to python int."""
    return [int(v) for v in values]


def _to_float_list(values, decimals: int = 1) -> List[float]:
    return [round(float(v), decimals) for v in values]


# ---------------------------------------------------------------------------
# 1. Calendar Heatmap
# ---------------------------------------------------------------------------

def build_calendar_heatmap(daily_commits: pd.Series) -> Timeline | Calendar:
    """提交热力图，支持按年切换。"""
    if daily_commits.empty:
        cal = Calendar(init_opts=opts.InitOpts(width="100%", height="220px"))
        cal.set_global_opts(title_opts=opts.TitleOpts(title="提交活动日历热力图"))
        return cal

    # 分年份数据
    all_dates = pd.Series(daily_commits.index)
    years = sorted(set(d.year for d in all_dates))

    if len(years) <= 1:
        # 单年直接返回 Calendar
        year = years[0]
        data = [[str(d), int(c)] for d, c in daily_commits.items()]
        max_val = int(daily_commits.max())
        cal = Calendar(init_opts=opts.InitOpts(width="100%", height="220px"))
        cal.add(
            series_name="提交数",
            yaxis_data=data,
            calendar_opts=opts.CalendarOpts(
                pos_top="40",
                pos_left="60",
                pos_right="30",
                range_=str(year),
                daylabel_opts=opts.CalendarDayLabelOpts(name_map="cn"),
                monthlabel_opts=opts.CalendarMonthLabelOpts(name_map="cn"),
            ),
        )
        cal.set_global_opts(
            title_opts=opts.TitleOpts(title="提交活动日历热力图", pos_left="center"),
            visualmap_opts=opts.VisualMapOpts(
                max_=max_val, min_=0, orient="horizontal",
                pos_top="180", pos_left="center",
                range_color=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
        return cal

    # 多年: 使用 Timeline
    tl = Timeline(init_opts=opts.InitOpts(width="100%", height="280px"))
    tl.add_schema(
        play_interval=3000,
        is_auto_play=False,
        pos_bottom="0",
        pos_left="center",
        width="60%",
    )

    max_val = int(daily_commits.max())

    for year in reversed(years):
        year_data = {
            d: c for d, c in daily_commits.items() if d.year == year
        }
        if not year_data:
            continue
        data = [[str(d), int(c)] for d, c in year_data.items()]
        cal = Calendar(init_opts=opts.InitOpts(width="100%", height="220px"))
        cal.add(
            series_name="提交数",
            yaxis_data=data,
            calendar_opts=opts.CalendarOpts(
                pos_top="40",
                pos_left="60",
                pos_right="30",
                range_=str(year),
                daylabel_opts=opts.CalendarDayLabelOpts(name_map="cn"),
                monthlabel_opts=opts.CalendarMonthLabelOpts(name_map="cn"),
            ),
        )
        cal.set_global_opts(
            title_opts=opts.TitleOpts(title="提交活动日历热力图", pos_left="center"),
            visualmap_opts=opts.VisualMapOpts(
                max_=max_val, min_=0, orient="horizontal",
                pos_top="180", pos_left="center",
                range_color=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
        tl.add(cal, str(year))

    return tl


# ---------------------------------------------------------------------------
# 2. Personnel Trend Chart
# ---------------------------------------------------------------------------

def build_personnel_trend_chart(monthly_trends: pd.DataFrame) -> Line:
    """人员变动趋势图（三条折线）。"""
    if monthly_trends.empty:
        return Line(init_opts=opts.InitOpts(width="100%", height="400px"))

    dates = [d.strftime("%Y-%m") for d in monthly_trends.index]

    line = Line(init_opts=opts.InitOpts(width="100%", height="400px"))
    line.add_xaxis(dates)

    line.add_yaxis(
        "累计开发者",
        _to_int_list(monthly_trends["cumulative_authors"]),
        is_smooth=True,
        is_symbol_show=False,
        linestyle_opts=opts.LineStyleOpts(width=3, color="#5470c6"),
        itemstyle_opts=opts.ItemStyleOpts(color="#5470c6"),
    )
    line.add_yaxis(
        "月活跃开发者",
        _to_int_list(monthly_trends["active_authors"]),
        is_smooth=True,
        linestyle_opts=opts.LineStyleOpts(width=2, color="#91cc75"),
        itemstyle_opts=opts.ItemStyleOpts(color="#91cc75"),
    )
    line.add_yaxis(
        "新增开发者",
        _to_int_list(monthly_trends["new_authors"]),
        is_smooth=True,
        linestyle_opts=opts.LineStyleOpts(width=2, color="#fac858"),
        itemstyle_opts=opts.ItemStyleOpts(color="#fac858"),
    )

    line.set_global_opts(
        title_opts=opts.TitleOpts(title="人员变动趋势", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(pos_bottom="0"),
        datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
        yaxis_opts=opts.AxisOpts(name="人数"),
    )
    return line


# ---------------------------------------------------------------------------
# 3. Activity Sunburst (3-layer ring)
# ---------------------------------------------------------------------------

def build_activity_sunburst(author_stats: pd.DataFrame) -> Sunburst:
    """开发者活跃状态环形图（三层）。"""
    if author_stats.empty:
        return Sunburst(init_opts=opts.InitOpts(width="100%", height="480px"))

    data = []
    for is_active, group1 in author_stats.groupby("is_active"):
        status_name = "活跃" if is_active else "不活跃"
        l2_children = []
        for phase, group2 in group1.groupby("phase"):
            l3_children = []
            for contrib, group3 in group2.groupby("contribution_level"):
                l3_children.append({"name": contrib, "value": len(group3)})
            l2_children.append({"name": phase, "children": l3_children})
        data.append({"name": status_name, "children": l2_children})

    sunburst = Sunburst(init_opts=opts.InitOpts(width="100%", height="480px"))
    sunburst.add(
        "",
        data_pair=data,
        radius=[0, "90%"],
        highlight_policy="ancestor",
        sort_="desc",
        levels=[
            {},
            {
                "r0": "0%", "r1": "25%",
                "itemStyle": {"borderWidth": 2},
                "label": {"fontSize": 12},
            },
            {
                "r0": "25%", "r1": "55%",
                "itemStyle": {"borderWidth": 2},
                "label": {"fontSize": 11},
            },
            {
                "r0": "55%", "r1": "90%",
                "itemStyle": {"borderWidth": 2},
                "label": {"fontSize": 10},
            },
        ],
    )
    sunburst.set_global_opts(
        title_opts=opts.TitleOpts(title="开发者活跃状态分布", pos_left="center"),
    )
    return sunburst


# ---------------------------------------------------------------------------
# 4. Lifecycle Scatter
# ---------------------------------------------------------------------------

def build_lifecycle_scatter(author_stats: pd.DataFrame) -> Scatter:
    """开发者生命周期散点图。"""
    if author_stats.empty:
        return Scatter(init_opts=opts.InitOpts(width="100%", height="460px"))

    scatter = Scatter(init_opts=opts.InitOpts(width="100%", height="460px"))

    for is_active in [True, False]:
        subset = author_stats[author_stats["is_active"] == is_active]
        if subset.empty:
            continue

        data = []
        for author_name, row in subset.iterrows():
            data.append([
                row["first_commit"].strftime("%Y-%m-%d"),
                row["last_commit"].strftime("%Y-%m-%d"),
                int(row["total_commits"]),
                str(author_name),
            ])

        color = "#2ecc71" if is_active else "#95a5a6"
        name = "活跃" if is_active else "不活跃"

        scatter.add_xaxis([d[0] for d in data])
        scatter.add_yaxis(
            name, data,
            symbol_size=JsCode("function(d){return Math.max(6, Math.sqrt(d[2])*2);}"),
            label_opts=opts.LabelOpts(
                is_show=True, position="right",
                formatter=JsCode("function(p){return p.value[3];}"),
            ),
            itemstyle_opts=opts.ItemStyleOpts(color=color),
        )

    scatter.set_global_opts(
        title_opts=opts.TitleOpts(title="开发者生命周期", pos_left="center"),
        xaxis_opts=opts.AxisOpts(
            type_="time", name="首次提交",
            splitline_opts=opts.SplitLineOpts(is_show=True),
        ),
        yaxis_opts=opts.AxisOpts(
            type_="time", name="最后提交",
            splitline_opts=opts.SplitLineOpts(is_show=True),
        ),
        tooltip_opts=opts.TooltipOpts(
            formatter=JsCode(
                "function(p){"
                "return '<b>'+p.value[3]+'</b><br/>"
                "首次: '+p.value[0]+'<br/>"
                "最后: '+p.value[1]+'<br/>"
                "提交: '+p.value[2];}"
            )
        ),
        legend_opts=opts.LegendOpts(pos_bottom="0"),
    )
    return scatter


# ---------------------------------------------------------------------------
# 5. Commit Rank (Horizontal Bar)
# ---------------------------------------------------------------------------

def build_commit_rank_bar(author_stats: pd.DataFrame) -> Bar:
    """提交排行榜 Top10 — 横向条形图。"""
    if author_stats.empty:
        return Bar(init_opts=opts.InitOpts(width="100%", height="400px"))

    top = author_stats.sort_values("total_commits", ascending=True).tail(10)
    names = [str(n) for n in top.index]
    values = _to_int_list(top["total_commits"])
    colors = ["#2ecc71" if a else "#95a5a6" for a in top["is_active"]]

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(names)
    bar.add_yaxis(
        "提交次数", values,
        label_opts=opts.LabelOpts(position="right"),
        itemstyle_opts=opts.ItemStyleOpts(
            color=JsCode(
                "function(p){var colors="
                + str(colors)
                + ";return colors[p.dataIndex];}"
            )
        ),
    )
    bar.reversal_axis()
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="提交榜 Top 10", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
        xaxis_opts=opts.AxisOpts(name="提交次数"),
        yaxis_opts=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(font_size=11),
        ),
        legend_opts=opts.LegendOpts(pos_bottom="0"),
    )
    return bar


# ---------------------------------------------------------------------------
# 6. Night Commit Rank (卷王榜)
# ---------------------------------------------------------------------------

def build_night_commit_rank(author_stats: pd.DataFrame) -> Bar:
    """卷王榜 Top10 — 夜间提交排行。"""
    if author_stats.empty:
        return Bar(init_opts=opts.InitOpts(width="100%", height="400px"))

    top = author_stats.sort_values("night_commits", ascending=True).tail(10)
    names = [str(n) for n in top.index]
    night_vals = _to_int_list(top["night_commits"])
    ratio_vals = _to_float_list(top["night_ratio"] * 100)
    total_vals = _to_int_list(top["total_commits"])

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(names)
    bar.add_yaxis(
        "夜间提交数", night_vals,
        label_opts=opts.LabelOpts(position="right"),
        itemstyle_opts=opts.ItemStyleOpts(
            color=JsCode(
                "new echarts.graphic.LinearGradient(0,0,1,0,"
                "[{offset:0,color:'#1a1a4e'},{offset:1,color:'#6c3fa0'}])"
            )
        ),
    )
    bar.reversal_axis()

    # 夜间占比折线 (使用 extend_axis + overlap)
    bar.extend_axis(
        xaxis=opts.AxisOpts(
            name="占比 %", min_=0, max_=100,
            position="top",
            axislabel_opts=opts.LabelOpts(formatter="{value}%"),
        )
    )

    line = Line()
    line.add_xaxis(names)
    line.add_yaxis(
        "夜间提交占比",
        ratio_vals,
        xaxis_index=1,
        label_opts=opts.LabelOpts(
            is_show=True,
            formatter=JsCode("function(p){return p.value+'%';}")
        ),
        linestyle_opts=opts.LineStyleOpts(width=2, color="#e040fb"),
        itemstyle_opts=opts.ItemStyleOpts(color="#e040fb"),
    )
    bar.overlap(line)

    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="卷王榜 Top 10 (20:00-06:00)", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(
            trigger="axis", axis_pointer_type="shadow",
            formatter=JsCode(
                "function(ps){"
                "var r='<b>'+ps[0].name+'</b>';"
                "for(var i=0;i<ps.length;i++){"
                "r+='<br/>'+ps[i].seriesName+': '+ps[i].value;"
                "}return r;}"
            ),
        ),
        xaxis_opts=opts.AxisOpts(name="夜间提交次数"),
        legend_opts=opts.LegendOpts(pos_bottom="0"),
    )
    return bar


# ---------------------------------------------------------------------------
# 7. Maintenance Rank (分段横向条形图)
# ---------------------------------------------------------------------------

def build_maintenance_rank(author_stats: pd.DataFrame) -> Bar:
    """最长维护榜 Top10。"""
    if author_stats.empty:
        return Bar(init_opts=opts.InitOpts(width="100%", height="400px"))

    top = author_stats.sort_values("maintenance_days", ascending=True).tail(10)
    names = [str(n) for n in top.index]

    ref_date = pd.Timestamp.now()
    one_year_ago = ref_date - pd.Timedelta(days=365)

    recent_days = []
    older_days = []
    for _, row in top.iterrows():
        total = row["maintenance_days"]
        start = row["first_commit"]
        end = row["last_commit"]
        if end < one_year_ago:
            recent_days.append(0)
            older_days.append(int(total))
        else:
            recent_start = max(start, one_year_ago)
            recent = max(0, (end - recent_start).days)
            recent_days.append(int(recent))
            older_days.append(int(total - recent))

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(names)
    bar.add_yaxis(
        "往期维护(天)", older_days, stack="stack",
        itemstyle_opts=opts.ItemStyleOpts(color="#b0bec5"),
        label_opts=opts.LabelOpts(is_show=False),
    )
    bar.add_yaxis(
        "近年维护(天)", recent_days, stack="stack",
        itemstyle_opts=opts.ItemStyleOpts(color="#1565c0"),
        label_opts=opts.LabelOpts(
            position="right",
            formatter=JsCode(
                "function(p){"
                "var t=p.value;"
                "for(var i=0;i<p.encode.x.length;i++){t+=0;}"
                "return p.value>0?p.value+'天':'';}"
            ),
        ),
    )
    bar.reversal_axis()
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="常青树榜 Top 10", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(
            trigger="axis", axis_pointer_type="shadow",
        ),
        xaxis_opts=opts.AxisOpts(name="维护天数"),
        legend_opts=opts.LegendOpts(pos_bottom="0"),
    )
    return bar


# ---------------------------------------------------------------------------
# 8. Code Activity Trend (双Y轴)
# ---------------------------------------------------------------------------

def build_code_activity_chart(code_activity: pd.DataFrame) -> Bar:
    """代码活动趋势图: 提交折线 + 增删行数柱状图。"""
    if code_activity.empty:
        return Bar(init_opts=opts.InitOpts(width="100%", height="400px"))

    dates = [d.strftime("%Y-%m") for d in code_activity.index]

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="400px"))
    bar.add_xaxis(dates)

    bar.add_yaxis(
        "新增行数",
        _to_int_list(code_activity["insertions"]),
        stack="lines",
        itemstyle_opts=opts.ItemStyleOpts(color="#66bb6a"),
        label_opts=opts.LabelOpts(is_show=False),
    )
    bar.add_yaxis(
        "删除行数",
        _to_int_list(code_activity["deletions"]),
        stack="lines_del",
        itemstyle_opts=opts.ItemStyleOpts(color="#ef5350"),
        label_opts=opts.LabelOpts(is_show=False),
    )

    # 提交折线 on secondary Y axis
    bar.extend_axis(
        yaxis=opts.AxisOpts(name="提交次数", position="right")
    )
    line = Line()
    line.add_xaxis(dates)
    line.add_yaxis(
        "提交数",
        _to_int_list(code_activity["commits"]),
        yaxis_index=1,
        is_smooth=True,
        linestyle_opts=opts.LineStyleOpts(width=2, color="#42a5f5"),
        itemstyle_opts=opts.ItemStyleOpts(color="#42a5f5"),
        label_opts=opts.LabelOpts(is_show=False),
    )
    bar.overlap(line)

    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="代码活动趋势", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
        legend_opts=opts.LegendOpts(pos_bottom="0"),
        yaxis_opts=opts.AxisOpts(name="代码行数"),
    )
    return bar


# ---------------------------------------------------------------------------
# 9. File Heatmap Sunburst
# ---------------------------------------------------------------------------

def build_file_heatmap_sunburst(file_heatmap: list[dict]) -> Sunburst:
    """文件修改热度旭日图。"""
    if not file_heatmap:
        sb = Sunburst(init_opts=opts.InitOpts(width="100%", height="500px"))
        sb.set_global_opts(title_opts=opts.TitleOpts(title="文件修改热度"))
        return sb

    sunburst = Sunburst(init_opts=opts.InitOpts(width="100%", height="500px"))
    sunburst.add(
        "",
        data_pair=file_heatmap,
        radius=[0, "90%"],
        highlight_policy="ancestor",
        sort_="desc",
        label_opts=opts.LabelOpts(is_show=False),
        levels=[
            {},
            {"r0": "0%", "r1": "20%", "itemStyle": {"borderWidth": 2}},
            {"r0": "20%", "r1": "45%", "itemStyle": {"borderWidth": 1}},
            {"r0": "45%", "r1": "70%", "itemStyle": {"borderWidth": 1}},
            {"r0": "70%", "r1": "92%", "itemStyle": {"borderWidth": 1}},
        ],
    )
    sunburst.set_global_opts(
        title_opts=opts.TitleOpts(title="文件修改热度", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(
            formatter=JsCode(
                "function(p){return '<b>'+p.name+'</b><br/>修改次数: '+(p.value||'');}",
            ),
        ),
    )
    return sunburst


# ---------------------------------------------------------------------------
# 10. Code Stability Analysis
# ---------------------------------------------------------------------------

def build_code_stability_chart(code_stability: pd.DataFrame) -> Bar:
    """代码稳定性分析 — 季度新增/删除行数趋势。"""
    if code_stability.empty:
        return Bar(init_opts=opts.InitOpts(width="100%", height="380px"))

    quarters = []
    for d in code_stability.index:
        q = (d.month - 1) // 3 + 1
        quarters.append(f"{d.year}-Q{q}")

    phase_colors = {"功能开发期": "#66bb6a", "重构期": "#ef5350", "稳定期": "#42a5f5"}

    bar = Bar(init_opts=opts.InitOpts(width="100%", height="380px"))
    bar.add_xaxis(quarters)
    bar.add_yaxis(
        "新增行数",
        _to_int_list(code_stability["insertions"]),
        itemstyle_opts=opts.ItemStyleOpts(color="#66bb6a"),
        label_opts=opts.LabelOpts(is_show=False),
    )
    bar.add_yaxis(
        "删除行数",
        _to_int_list(code_stability["deletions"]),
        itemstyle_opts=opts.ItemStyleOpts(color="#ef5350"),
        label_opts=opts.LabelOpts(is_show=False),
    )

    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="代码稳定性分析", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
        legend_opts=opts.LegendOpts(pos_bottom="0"),
        yaxis_opts=opts.AxisOpts(name="代码行数"),
    )
    return bar


# ---------------------------------------------------------------------------
# 11. Developer Detail Panel (个人分析)
# ---------------------------------------------------------------------------

def build_developer_24h_radar(df_author: pd.DataFrame, author_name: str) -> Radar:
    """24小时提交分布雷达图。"""
    # 统计每个小时的提交数
    hour_counts = [0] * 24
    for _, row in df_author.iterrows():
        h = int(row["hour"])
        hour_counts[h] += 1

    max_val = max(hour_counts) if hour_counts else 1

    radar = Radar(init_opts=opts.InitOpts(width="100%", height="350px"))
    schema = [
        opts.RadarIndicatorItem(name=f"{h}:00", max_=max_val)
        for h in range(24)
    ]
    radar.add_schema(schema=schema)
    radar.add(
        author_name,
        [hour_counts],
        linestyle_opts=opts.LineStyleOpts(width=2, color="#5470c6"),
        areastyle_opts=opts.AreaStyleOpts(opacity=0.3, color="#5470c6"),
    )
    radar.set_global_opts(
        title_opts=opts.TitleOpts(title="24小时提交分布", pos_left="center"),
    )
    return radar


def build_developer_calendar(df_author: pd.DataFrame) -> Calendar | Timeline:
    """个人提交日历热力图。"""
    daily = df_author.groupby("date_6am_cutoff").size()
    return build_calendar_heatmap(daily)


def build_developer_detail_charts(
    prepared_df: pd.DataFrame,
    author_name: str,
    author_stats: pd.DataFrame,
) -> Dict[str, Any]:
    """
    为指定开发者构建个人面板所需的所有数据和图表。

    Returns dict with keys: info, radar_html, calendar_html
    """
    df_author = prepared_df[prepared_df["author"] == author_name].copy()

    if df_author.empty:
        return {}

    # 个人信息
    stats_row = author_stats.loc[author_name] if author_name in author_stats.index else None
    info = {}
    if stats_row is not None:
        info = {
            "name": author_name,
            "email": stats_row.get("email", ""),
            "first_commit": str(stats_row["first_commit"].date()) if pd.notna(stats_row["first_commit"]) else "",
            "last_commit": str(stats_row["last_commit"].date()) if pd.notna(stats_row["last_commit"]) else "",
            "total_commits": int(stats_row["total_commits"]),
            "total_insertions": int(stats_row.get("total_insertions", 0)),
            "total_deletions": int(stats_row.get("total_deletions", 0)),
            "maintenance_days": int(stats_row["maintenance_days"]),
            "is_active": bool(stats_row["is_active"]),
            "night_commits": int(stats_row["night_commits"]),
            "night_ratio": round(float(stats_row["night_ratio"]) * 100, 1),
        }

    # 24小时雷达图
    radar = build_developer_24h_radar(df_author, author_name)

    # 个人日历
    calendar = build_developer_calendar(df_author)

    return {
        "info": info,
        "radar": radar,
        "calendar": calendar,
    }
