from __future__ import annotations

from typing import Dict

from pyecharts import options as opts
from pyecharts.charts import Bar, Page, Pie

from analysis import PERIOD_ORDER


def build_period_bar(period_stats: Dict[str, Dict[str, object]]) -> Bar:
    labels = PERIOD_ORDER
    values = [period_stats[label]["count"] for label in labels]
    return (
        Bar()
        .add_xaxis(labels)
        .add_yaxis("提交次数", values)
        .set_global_opts(
            title_opts=opts.TitleOpts(title="晚间提交分布"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=15)),
        )
    )


def build_after18_pie(total_commits: int, after_18_count: int) -> Pie:
    before_18_count = max(total_commits - after_18_count, 0)
    data = [
        ("18:00后提交", after_18_count),
        ("18:00前提交", before_18_count),
    ]
    return (
        Pie()
        .add("提交占比", data)
        .set_global_opts(title_opts=opts.TitleOpts(title="18:00后提交占比"))
        .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
    )


def build_top_authors_bar(author_counts) -> Bar:
    labels = list(author_counts.index)
    values = list(author_counts.values)
    if not labels:
        labels = ["无"]
        values = [0]

    return (
        Bar()
        .add_xaxis(labels)
        .add_yaxis("提交次数", values)
        .set_global_opts(title_opts=opts.TitleOpts(title="Top 作者提交次数"))
    )


def render_charts(metrics: Dict[str, object], period_stats: Dict[str, Dict[str, object]], output_file: str) -> str:
    page = Page(page_title="Git 开发者洞察")
    page.add(
        build_period_bar(period_stats),
        build_after18_pie(metrics["total_commits"], metrics["after_18_count"]),
        build_top_authors_bar(metrics["overall_author_counts"]),
    )
    page.render(output_file)
    return output_file
