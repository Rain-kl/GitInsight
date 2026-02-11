from __future__ import annotations

from typing import Dict

import pandas as pd

from analysis import PERIOD_ORDER


def export_csv(
    output_file: str,
    metrics: Dict[str, object],
    period_stats: Dict[str, Dict[str, object]],
    top_authors: Dict[str, Dict[str, object]],
) -> str:
    report_data = {
        "指标": [
            "总参与开发者人数",
            "总提交次数",
            "全局最晚提交时间（以06:00为一天分界）",
            "最晚提交者",
            "每天最晚提交中位数（以06:00为一天分界）",
            "18:00后提交占比",
            "最卷开发者",
            "其深夜提交次数",
            "18:00-19:00提交次数",
            "18:00-19:00提交占比",
            "18:00-19:00最多提交者",
            "19:00-20:00提交次数",
            "19:00-20:00提交占比",
            "19:00-20:00最多提交者",
            "20:00-次日06:00提交次数",
            "20:00-次日06:00提交占比",
            "20:00-次日06:00最多提交者",
        ],
        "值": [
            metrics["total_authors"],
            metrics["total_commits"],
            metrics["latest_time_display"],
            metrics["latest_author"],
            metrics["median_time_str"],
            f"{metrics['after_18_pct']:.1f}%",
            metrics["most_night_author"],
            metrics["most_night_count"],
            period_stats["18:00-19:00"]["count"],
            f"{period_stats['18:00-19:00']['percentage']:.1f}%",
            f"{top_authors['18:00-19:00']['author']}（{top_authors['18:00-19:00']['count']}次）",
            period_stats["19:00-20:00"]["count"],
            f"{period_stats['19:00-20:00']['percentage']:.1f}%",
            f"{top_authors['19:00-20:00']['author']}（{top_authors['19:00-20:00']['count']}次）",
            period_stats["20:00-次日06:00"]["count"],
            f"{period_stats['20:00-次日06:00']['percentage']:.1f}%",
            f"{top_authors['20:00-次日06:00']['author']}（{top_authors['20:00-次日06:00']['count']}次）",
        ],
    }
    report_df = pd.DataFrame(report_data)
    report_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def print_summary(
    metrics: Dict[str, object],
    filter_stats,
    outputs: Dict[str, str],
    period_stats: Dict[str, Dict[str, object]],
    top_authors: Dict[str, Dict[str, object]],
) -> None:
    print("\n📊 开发者洞察概要（06:00 为一天分界）")
    print("-" * 40)
    print(f"总提交次数：{metrics['total_commits']}（过滤前 {filter_stats.before}，过滤掉 {filter_stats.removed} 条自动化提交）")
    print(f"参与开发者人数：{metrics['total_authors']}")
    print(f"全局最晚提交时间：{metrics['latest_time_display']}（{metrics['latest_author']}）")
    print(f"每天最晚提交中位数：{metrics['median_time_str']}")
    print(f"18:00后提交占比：{metrics['after_18_pct']:.1f}%（{metrics['after_18_count']} 次）")
    print(f"最卷开发者：{metrics['most_night_author']}（深夜提交 {metrics['most_night_count']} 次）")
    print("\n📁 产出文件")
    print(f"- CSV：{outputs['csv']}")
    print(f"- 图表：{outputs['html']}")

    print("\n📌 晚间分段统计")
    for label in PERIOD_ORDER:
        stats = period_stats[label]
        top_author = top_authors[label]
        print(
            f"{label}：{stats['count']} 次（{stats['percentage']:.1f}%），"
            f"最多提交者 {top_author['author']}（{top_author['count']} 次）"
        )
