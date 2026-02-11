from __future__ import annotations

import datetime
from typing import Dict, List

import pandas as pd  # Add this
from pyecharts import options as opts
from pyecharts.charts import Bar, Calendar, Line, Page, Pie, Tab, Scatter, Sunburst, Grid
from pyecharts.globals import ThemeType, SymbolType
from pyecharts.commons.utils import JsCode


def _convert_to_python_int(values) -> List[int]:
    """Helper to convert numpy/pandas integers to python int to avoid serialization errors."""
    return [int(v) for v in values]


def build_calendar_heatmap(daily_commits) -> Calendar:
    """提交热力图 (最近一年)"""
    if daily_commits.empty:
        data = []
        max_val = 0
        current_year = datetime.date.today().year
        range_date = str(current_year)
    else:
        # Pyecharts Calendar expects [[date, value], ...]
        data = [
            [str(date), int(count)]
            for date, count in daily_commits.items()
        ]
        max_val = int(daily_commits.max())
        
        max_date = daily_commits.index.max()
        min_date = daily_commits.index.min()
        
        # 为了保证显示效果，默认只显示最近 12 个月 + 本月
        # 如果数据少于 1 年，显示全部
        if (max_date - min_date).days > 365:
            start_date = max_date - datetime.timedelta(days=365)
            range_date = [str(start_date), str(max_date)]
        else:
            range_date = [str(min_date), str(max_date)]

    calendar = Calendar(init_opts=opts.InitOpts(theme=ThemeType.MACARONS, width="95%", height="280px"))
    calendar.add(
        series_name="",
        yaxis_data=data,
        calendar_opts=opts.CalendarOpts(
            pos_top="60",
            pos_left="center",
            range_=range_date,
            yearlabel_opts=opts.CalendarYearLabelOpts(is_show=True),
            daylabel_opts=opts.CalendarDayLabelOpts(name_map="cn"),
            monthlabel_opts=opts.CalendarMonthLabelOpts(name_map="cn"),
        ),
    )
    calendar.set_global_opts(
        title_opts=opts.TitleOpts(title="提交热力图 (GitHub Style)", pos_left="center"),
        visualmap_opts=opts.VisualMapOpts(
            max_=max_val,
            min_=0,
            orient="horizontal",
            is_piecewise=False,
            pos_top="230",
            pos_left="center",
            is_calculable=True,
            range_color=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
        ),
        legend_opts=opts.LegendOpts(is_show=False)
    )
    return calendar


def build_personnel_trend_chart(monthly_trends) -> Line:
    """人员变动趋势图 (Requirement 2.1.1)"""
    if monthly_trends.empty:
        return Line()
    
    dates = [d.strftime("%Y-%m") for d in monthly_trends.index]
    
    line = Line(init_opts=opts.InitOpts(theme=ThemeType.CHALK, width="100%", height="450px"))
    line.add_xaxis(dates)
    
    line.add_yaxis(
        "累计开发者",
        _convert_to_python_int(monthly_trends["cumulative_authors"]),
        is_smooth=True,
        is_symbol_show=False,
        linestyle_opts=opts.LineStyleOpts(width=3),
    )
    line.add_yaxis(
        "月活跃开发者",
        _convert_to_python_int(monthly_trends["active_authors"]),
        is_smooth=True,
        itemstyle_opts=opts.ItemStyleOpts(color="#91cc75"),
    )
    line.add_yaxis(
        "新增开发者",
        _convert_to_python_int(monthly_trends["new_authors"]),
        is_smooth=True,
        itemstyle_opts=opts.ItemStyleOpts(color="#fac858"),
    )
    
    line.set_global_opts(
        title_opts=opts.TitleOpts(title="人员变动趋势", pos_left="center"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(pos_top="5%"),
        datazoom_opts=[opts.DataZoomOpts(range_start=0, range_end=100)],
        yaxis_opts=opts.AxisOpts(name="人数"),
    )
    return line


def build_activity_sunburst(author_stats) -> Sunburst:
    """开发者活跃状态环形图 (Requirement 2.1.2)"""
    if author_stats.empty:
        return Sunburst()

    # 构建层级数据: 活跃状态 -> 参与阶段 -> 贡献程度
    # Data structure: [{"name": "Active", "children": [...]}]
    
    data = []
    
    # helper
    def get_children(df, group_col, next_col=None):
        groups = df.groupby(group_col)
        children = []
        for name, group in groups:
            node = {"name": str(name), "value": len(group)}
            if next_col:
                # Recursive
                # Check if next_col is the last one
                if next_col == "contribution_level":
                    sub_children = get_children(group, next_col, None)
                else:
                    # Should not happen in this fixed 3-level definition
                    sub_children = []
                
                if sub_children:
                    node["children"] = sub_children
            children.append(node)
        return children

    # Level 1: Active Status
    for is_active, group1 in author_stats.groupby("is_active"):
        status_name = "活跃" if is_active else "不活跃"
        
        # Level 2: Phase
        l2_children = []
        for phase, group2 in group1.groupby("phase"):
            
            # Level 3: Contribution
            l3_children = []
            for contrib, group3 in group2.groupby("contribution_level"):
                l3_children.append({"name": contrib, "value": len(group3)})
            
            l2_children.append({"name": phase, "children": l3_children})
            
        data.append({"name": status_name, "children": l2_children})

    sunburst = Sunburst(init_opts=opts.InitOpts(theme=ThemeType.MACARONS, height="500px"))
    sunburst.add(
        "",
        data_pair=data,
        radius=[0, "90%"],
        highlight_policy="ancestor",
        sort_="desc",
        levels=[
            {},
            {"r0": "0%", "r1": "25%", "itemStyle": {"borderWidth": 2}},
            {"r0": "25%", "r1": "60%", "itemStyle": {"borderWidth": 2}},
            {"r0": "60%", "r1": "95%", "itemStyle": {"borderWidth": 2}},
        ],
    )
    sunburst.set_global_opts(
        title_opts=opts.TitleOpts(title="开发者活跃状态分布", pos_left="center"),
    )
    return sunburst


def build_lifecycle_scatter(author_stats) -> Scatter:
    """开发者生命周期散点图 (Requirement 2.1.3)"""
    if author_stats.empty:
        return Scatter()

    # X: First Commit Date, Y: Last Commit Date
    # Size: total_commits
    
    # 转换为时间戳以便绘图? Or simple string YYYY-MM-DD
    # E-charts Scatter supports time axis.
    
    # Pyecharts data: [[x, y, extra_data...]]
    # We can use Javascript callback to format size and color, but simpler is multiple series (Active vs Inactive)
    
    scatter = Scatter(init_opts=opts.InitOpts(theme=ThemeType.WALDEN, height="500px"))
    
    for is_active in [True, False]:
        subset = author_stats[author_stats["is_active"] == is_active]
        if subset.empty:
            continue
            
        data = []
        names = []
        for author, row in subset.iterrows():
            # X: First, Y: Last
            data.append([
                row["first_commit"].strftime("%Y-%m-%d"), 
                row["last_commit"].strftime("%Y-%m-%d"),
                int(row["total_commits"]), # value[2] for symbol size
                author
            ])
        
        color = "#2ecc71" if is_active else "#95a5a6"
        name = "活跃" if is_active else "不活跃"
        
        scatter.add_xaxis([d[0] for d in data]) # Dummy xaxis data needed? No, scatter takes xy in add_yaxis
        
        # Correct usage: add_yaxis(series_name, data_pair=[[x, y, ...]])
        # Note: add_xaxis expects X values if using category axis. For Time axis, we set axis type.
        
        scatter.add_yaxis(
            name,
            data,
            # Normalize symbol size: log scale or sqrt to avoid huge bubbles
            symbol_size=JsCode("function (data) { return Math.sqrt(data[2]) * 1.5; }"),
            label_opts=opts.LabelOpts(
                is_show=True, position="right", formatter=JsCode("function(params){return params.value[3];}")
            ),
            itemstyle_opts=opts.ItemStyleOpts(color=color)
        )

    scatter.set_global_opts(
        title_opts=opts.TitleOpts(title="开发者生命周期", pos_left="center"),
        xaxis_opts=opts.AxisOpts(
            type_="time", 
            name="首次提交", 
            splitline_opts=opts.SplitLineOpts(is_show=True)
        ),
        yaxis_opts=opts.AxisOpts(
            type_="time", 
            name="最后提交",
            splitline_opts=opts.SplitLineOpts(is_show=True)
        ),
        tooltip_opts=opts.TooltipOpts(
            formatter=JsCode(
                "function (params) { "
                "return '<b>' + params.value[3] + '</b><br/>' + "
                "'First: ' + params.value[0] + '<br/>' + "
                "'Last: ' + params.value[1] + '<br/>' + "
                "'Commits: ' + params.value[2]; }"
            )
        )
    )
    return scatter


def build_rank_charts(author_stats) -> Tab:
    """三大排行榜 (Requirement 2.2)"""
    tab = Tab()
    if author_stats.empty:
        return tab
    
    # 1. 提交榜 (Top 10 Total Commits)
    top_commits = author_stats.sort_values("total_commits", ascending=False).head(10)
    bar1 = Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
    bar1.add_xaxis(top_commits.index.tolist())
    bar1.add_yaxis("提交总数", _convert_to_python_int(top_commits["total_commits"]))
    bar1.set_global_opts(
         title_opts=opts.TitleOpts(title="提交榜 Top 10"),
         xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20)),
    )
    tab.add(bar1, "提交榜")

    # 2. 卷王榜 (Top 10 Night Commits)
    # 叠加: Night Commits (Bar) + Night Ratio (Line) -> Need Overlap or Dual Y
    # Using Grid/Overlap? Tab accepts BaseChart.
    # Bar with multiple y-axis
    
    top_night = author_stats.sort_values("night_commits", ascending=False).head(10)
    
    bar2 = Bar(init_opts=opts.InitOpts(theme=ThemeType.DARK)) # 深夜主题
    bar2.add_xaxis(top_night.index.tolist())
    bar2.add_yaxis("夜间提交数", _convert_to_python_int(top_night["night_commits"]), label_opts=opts.LabelOpts(is_show=True))
    
    # Create a line for ratio on secondary axis
    line2 = Line()
    line2.add_xaxis(top_night.index.tolist())
    line2.add_yaxis(
        "夜间占比", 
        [round(x * 100, 1) for x in top_night["night_ratio"]],
        yaxis_index=1,
        label_opts=opts.LabelOpts(is_show=False)
    )
    
    bar2.extend_axis(yaxis=opts.AxisOpts(name="占比 %", min_=0, max_=100))
    bar2.set_global_opts(
        title_opts=opts.TitleOpts(title="卷王榜 Top 10 (20:00-06:00)"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20))
    )
    bar2.overlap(line2)
    tab.add(bar2, "卷王榜")

    # 3. 最长维护榜
    # Top 10 by maintenance_days
    # Stacked bar: Recent (<365 days) vs Older
    
    top_maint = author_stats.sort_values("maintenance_days", ascending=False).head(10)
    
    # Calculate segments
    # Assuming "Recent" = overlap with last 365 days relative to TODAY (or repo max date)
    # But strictly: "Maintenance duration from first to last".
    # Req: "Deep color: Recent 1 year maintenance", "Light: > 1 year ago"
    
    # Analyze timezone of first element to decide how to generate current time
    first_ts = top_maint["last_commit"].iloc[0]
    if first_ts.tzinfo:
        ref_date = pd.Timestamp.now(tz=first_ts.tzinfo)
    else:
        # If naive, assume it's consistent and use naive now (or target specific tz converted to naive)
        # Here we hardcode offset matching analysis.py if possible, or just use system time
        # Better: use the max date from the data as reference? 
        # But 'maintenance' implies 'active status' so relative to real wall clock is usually desired.
        ref_date = pd.Timestamp.now().replace(tzinfo=None)

    one_year_ago = ref_date - pd.Timedelta(days=365)
    
    recent_days = []
    older_days = []
    
    for _, row in top_maint.iterrows():
        total = row["maintenance_days"]
        start = row["first_commit"]
        end = row["last_commit"]
        
        # Logic: 
        # Intersection of [start, end] and [one_year_ago, ref_date] is "Recent"
        # Intersection of [start, end] and [min, one_year_ago] is "Older"
        
        # Simplified:
        if end < one_year_ago:
            # Entirely in past
            recent = 0
            older = total
        else:
            # Overlaps with recent year
            # Start of recent period for this user is max(start, one_year_ago)
            recent_start = max(start, one_year_ago)
            # Duration in recent
            recent = (end - recent_start).days
            if recent < 0: recent = 0
            older = total - recent
            
        recent_days.append(int(recent))
        older_days.append(int(older))

    bar3 = Bar(init_opts=opts.InitOpts(theme=ThemeType.VINTAGE))
    bar3.add_xaxis(top_maint.index.tolist())
    bar3.add_yaxis("往期维护(天)", older_days, stack="stack1", color="#d1d5db") # local variable color
    bar3.add_yaxis("近期维护(天)", recent_days, stack="stack1", color="#374151") 
    
    bar3.set_global_opts(
         title_opts=opts.TitleOpts(title="常青树榜 Top 10"),
         xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=20)),
    )
    tab.add(bar3, "最长维护榜")
    
    # Fix for Tab object missing width attribute in Page render
    tab.width = "100%"
    return tab


def render_charts(metrics: Dict[str, object], output_file: str) -> str:
    """生成组合图表报告"""
    monthly_trends = metrics.get("monthly_trends", pd.DataFrame())
    author_stats = metrics.get("author_stats", pd.DataFrame())
    
    # 2.1.1
    trend_chart = build_personnel_trend_chart(monthly_trends)
    # 2.1.2
    sunburst = build_activity_sunburst(author_stats)
    # 2.1.3
    scatter = build_lifecycle_scatter(author_stats)
    # 2.2
    rank_tabs = build_rank_charts(author_stats)

    page = Page(layout=Page.SimplePageLayout, page_title="Git 项目人员分析报告")
    
    page.add(trend_chart)
    page.add(sunburst)
    page.add(scatter)
    page.add(rank_tabs)
    
    page.render(output_file)
    return output_file

