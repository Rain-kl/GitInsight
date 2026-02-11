"""
report.py — 控制台摘要输出。
"""
from __future__ import annotations

from typing import Dict


def print_summary(
    metrics: Dict[str, object],
    filter_stats,
    outputs: Dict[str, str],
) -> None:
    print("\n" + "=" * 50)
    print(" Git 项目人员分析报告摘要")
    print("=" * 50)
    print(f"总提交次数: {metrics.get('total_commits', 0):,} (过滤前 {filter_stats.before:,}, 过滤掉 {filter_stats.removed:,} 条自动化提交)")
    print(f"参与开发者: {metrics.get('total_authors', 0)} 人")
    print(f"活跃开发者(近半年): {metrics.get('active_authors_6m', 0)} 人")
    print(f"代码净增长: {metrics.get('net_lines', 0):+,} 行")
    print(f"项目生命周期: {metrics.get('project_lifecycle_days', 0):,} 天")
    print(f"数据范围: {metrics.get('date_range', '无')}")
    print("-" * 50)
    print("[产出文件]")
    print(f"  可视化仪表板: {outputs.get('html', '')}")
    print("=" * 50)
