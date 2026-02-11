from __future__ import annotations

from typing import Dict

import pandas as pd


def export_csv(
    output_file: str,
    metrics: Dict[str, object],
) -> str:
    def format_top_list(series: pd.Series) -> str:
        if series is None or series.empty:
            return "无"
        return "；".join([f"{name}（{count}次）" for name, count in series.items()])

    report_data = {
        "指标": [
            "总参与开发者人数",
            "总提交次数",
            "统计起止日期（以06:00为一天分界）",
            "近2个月活跃人数",
            "近1年不活跃人数",
            "Top10 总提交量排名",
            "Top10 20:00-06:00 提交量排名",
            "Top10 最近3个月提交量排名",
        ],
        "值": [
            metrics["total_authors"],
            metrics["total_commits"],
            metrics["date_range"],
            metrics["active_recent_2m"],
            metrics["inactive_1y"],
            format_top_list(metrics["overall_author_counts"]),
            format_top_list(metrics["night_author_counts"]),
            format_top_list(metrics["recent_3m_author_counts"]),
        ],
    }
    report_df = pd.DataFrame(report_data)
    report_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def print_summary(
    metrics: Dict[str, object],
    filter_stats,
    outputs: Dict[str, str],
) -> None:
    print("\n📊 开发者洞察概要（06:00 为一天分界）")
    print("-" * 40)
    print(f"总提交次数：{metrics['total_commits']}（过滤前 {filter_stats.before}，过滤掉 {filter_stats.removed} 条自动化提交）")
    print(f"参与开发者人数：{metrics['total_authors']}")
    print(f"统计起止日期：{metrics['date_range']}")
    print(f"近2个月活跃人数：{metrics['active_recent_2m']}")
    print(f"近1年不活跃人数：{metrics['inactive_1y']}")
    print("\n📁 产出文件")
    print(f"- CSV：{outputs['csv']}")
    print(f"- 图表：{outputs['html']}")
