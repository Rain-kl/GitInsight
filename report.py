from __future__ import annotations

from typing import Dict


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
    print(f"- 图表：{outputs['html']}")
