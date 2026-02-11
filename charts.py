from __future__ import annotations

import datetime
from typing import Dict, List

from pyecharts import options as opts
from pyecharts.charts import Bar, Calendar, Line, Page, Pie, Tab
from pyecharts.globals import ThemeType
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


def build_daily_trend_line(daily_commits) -> Line:
    """每日提交趋势"""
    if daily_commits.empty:
        dates = []
        counts = []
    else:
        dates = [str(d) for d in daily_commits.index]
        counts = _convert_to_python_int(daily_commits.values)

    line = Line(init_opts=opts.InitOpts(theme=ThemeType.MACARONS, width="95%", height="400px"))
    line.add_xaxis(dates)
    line.add_yaxis(
        "提交次数",
        counts,
        is_smooth=True,
        symbol="emptyCircle",
        symbol_size=6,
        areastyle_opts=opts.AreaStyleOpts(opacity=0.3, color="#5470c6"),
        label_opts=opts.LabelOpts(is_show=False),
        markpoint_opts=opts.MarkPointOpts(
            data=[opts.MarkPointItem(type_="max", name="最大值")]
        ),
    )
    line.set_global_opts(
        title_opts=opts.TitleOpts(title="每日提交趋势", pos_left="center", pos_top="10"),
        xaxis_opts=opts.AxisOpts(
            type_="category",
            boundary_gap=False,
            axislabel_opts=opts.LabelOpts(rotate=0), # 让 DataZoom 处理显示密度
        ),
        yaxis_opts=opts.AxisOpts(
            type_="value",
            splitline_opts=opts.SplitLineOpts(is_show=True),
        ),
        datazoom_opts=[
            opts.DataZoomOpts(type_="slider", range_start=0, range_end=100, pos_bottom="0%"),
            opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
        ],
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
    )
    return line


def build_author_ranking_bar(author_counts, title: str, color: str = None) -> Bar:
    """通用排名柱状图"""
    if(author_counts.empty):
        authors = []
        counts = []
    else:
        authors = list(author_counts.index)
        counts = _convert_to_python_int(author_counts.values)

    bar = Bar(init_opts=opts.InitOpts(theme=ThemeType.MACARONS, height="500px"))
    bar.add_xaxis(authors)
    bar.add_yaxis(
        "提交数", 
        counts, 
        itemstyle_opts=opts.ItemStyleOpts(color=color) if color else None,
        category_gap="40%"
    )
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title=title, pos_left="left"),
        xaxis_opts=opts.AxisOpts(
            axislabel_opts=opts.LabelOpts(rotate=30, interval=0, font_size=11)
        ),
        yaxis_opts=opts.AxisOpts(name="提交次数"),
        tooltip_opts=opts.TooltipOpts(trigger="item"),
        datazoom_opts=[
             opts.DataZoomOpts(type_="slider", show_detail=False, pos_bottom="5%") if len(authors) > 15 else None
        ]
    )
    # 移除 None (如果不需要 DataZoom)
    if not bar.options.get("dataZoom"):
        del bar.options["dataZoom"]

    return bar


def build_activity_pie(total_authors: int, active_recent_2m: int, inactive_1y: int) -> Pie:
    """活跃度分布饼图"""
    # 计算中间状态人数
    medium_active = total_authors - active_recent_2m - inactive_1y
    if medium_active < 0: 
        medium_active = 0

    data_pair = [
        ("近期活跃 (2月内)", active_recent_2m),
        ("平稳开发者 (2月-1年)", medium_active),
        ("已沉寂 (>1年)", inactive_1y),
    ]
    
    # 过滤掉 0 的项，避免饼图太丑
    data_pair = [d for d in data_pair if d[1] > 0]

    pie = Pie(init_opts=opts.InitOpts(theme=ThemeType.MACARONS, width="100%", height="400px"))
    pie.add(
        "",
        data_pair,
        radius=["40%", "70%"],
        rosetype="radius",
        label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)"),
    )
    pie.set_global_opts(
        title_opts=opts.TitleOpts(title="开发者活跃状态", pos_left="center"),
        legend_opts=opts.LegendOpts(orient="vertical", pos_top="20%", pos_left="5%"),
    )
    return pie


def render_charts(metrics: Dict[str, object], output_file: str) -> str:
    """生成组合图表报告"""
    
    # 1. 提交热力图
    calendar = build_calendar_heatmap(metrics["daily_commits"])
    
    # 2. 趋势图
    trend_line = build_daily_trend_line(metrics["daily_commits"])
    
    # 3. 贡献者榜单 (Tab 组合)
    rank_tab = Tab()
    rank_tab.add(
        build_author_ranking_bar(metrics["overall_author_counts"], "贡献总榜 Top 10", "#5470c6"),
        "总榜 Top10"
    )
    rank_tab.add(
        build_author_ranking_bar(metrics["recent_3m_author_counts"], "近期黑马 Top 10 (近3个月)", "#91cc75"),
        "近期活跃"
    )
    rank_tab.add(
        build_author_ranking_bar(metrics["night_author_counts"], "深夜战神 Top 10 (20:00-06:00)", "#fac858"),
        "深夜提交"
    )
    
    # Fix for Tab object missing width attribute in Page render
    rank_tab.width = "100%"

    # 4. 活跃度分布
    activity_pie = build_activity_pie(
        metrics["total_authors"], 
        metrics["active_recent_2m"], 
        metrics["inactive_1y"]
    )
    
    # 页面布局
    page = Page(layout=Page.SimplePageLayout, page_title="Git 项目洞察报告")
    
    # 添加各个组件
    # 注意：Page 会按顺序渲染 HTML
    page.add(calendar)
    page.add(trend_line)
    # 将 Tab 和 Pie 并列不太容易 (Grid 不支持 Tab)，所以上下排列
    page.add(rank_tab)
    page.add(activity_pie)
    
    page.render(output_file)
    return output_file
