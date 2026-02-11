"""
analysis.py — 数据分析引擎。

职责:
  - 过滤自动化提交
  - 解析时间字段并补充分析所需列
  - 计算月度人员变动趋势
  - 计算作者维度统计（活跃状态、参与阶段、贡献程度、夜间提交等）
  - 计算代码活动趋势（月度增删行数）
  - 计算文件修改热度
  - 计算代码稳定性分析
  - 汇总核心指标
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional

import pandas as pd
from tqdm import tqdm

TARGET_TZ = "Asia/Shanghai"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FilterStats:
    before: int
    removed: int
    after: int


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def get_adjusted_time_in_6am_day(timestamp: pd.Timestamp) -> float:
    """
    以 06:00 为一天分界，返回调整后的时间（小时+分钟的小数）。
    00:00 -> 24.0, 05:59 -> 29.98, 06:00 -> 6.0, 23:59 -> 23.98
    """
    hour = timestamp.hour
    minute = timestamp.minute
    second = timestamp.second
    adjusted_hour = hour + 24 if hour < 6 else hour
    return adjusted_hour + minute / 60.0 + second / 3600.0


def get_commit_date_with_6am_cutoff(timestamp: pd.Timestamp):
    """以 06:00 为分界点，凌晨提交算作前一天。"""
    if timestamp.hour < 6:
        return (timestamp - timedelta(days=1)).date()
    return timestamp.date()


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_automated_commits(df: pd.DataFrame) -> tuple[pd.DataFrame, FilterStats]:
    """过滤时区为 +0000 的自动化提交。"""
    before = len(df)

    def _is_automated(datetime_str: str) -> bool:
        if pd.isna(datetime_str):
            return True
        return str(datetime_str).strip().endswith("+0000")

    filtered = df[~df["datetime_str"].apply(_is_automated)].copy()
    after = len(filtered)
    return filtered, FilterStats(before=before, removed=before - after, after=after)


# ---------------------------------------------------------------------------
# DataFrame preparation
# ---------------------------------------------------------------------------

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """解析时间并补充分析所需字段。"""
    df = df.copy()
    df["datetime_utc"] = pd.to_datetime(
        df["datetime_str"],
        format="%Y-%m-%d %H:%M:%S %z",
        utc=True,
        errors="coerce",
    )
    df = df.dropna(subset=["datetime_utc"]).copy()
    if df.empty:
        return df

    # Enable tqdm for pandas
    tqdm.pandas(desc="Processing timestamps", leave=False)

    df["local_time"] = df["datetime_utc"].dt.tz_convert(TARGET_TZ).dt.tz_localize(None)
    df["hour"] = df["local_time"].dt.hour
    df["minute"] = df["local_time"].dt.minute
    df["second"] = df["local_time"].dt.second
    df["date"] = df["local_time"].dt.date
    df["adjusted_time"] = df["local_time"].progress_apply(get_adjusted_time_in_6am_day)
    df["date_6am_cutoff"] = df["local_time"].progress_apply(get_commit_date_with_6am_cutoff)
    df["time_in_6am_day"] = df["adjusted_time"]

    return df


# ---------------------------------------------------------------------------
# Time range filtering
# ---------------------------------------------------------------------------

def filter_by_time_range(
    df: pd.DataFrame,
    period: str = "all",
    ref_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    按时间范围筛选数据。

    period: 'half_year' | 'one_year' | 'five_years' | 'all'
    """
    if period == "all" or df.empty:
        return df

    if ref_date is None:
        ref_date = pd.Timestamp.now()

    days_map = {
        "half_year": 180,
        "one_year": 365,
        "five_years": 1825,
    }
    days = days_map.get(period)
    if days is None:
        return df

    cutoff = ref_date - pd.Timedelta(days=days)
    return df[df["local_time"] >= cutoff].copy()


# ---------------------------------------------------------------------------
# Monthly personnel trends
# ---------------------------------------------------------------------------

def compute_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """计算每月的人员变动趋势。"""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["month_date"] = (
        pd.to_datetime(df["date_6am_cutoff"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # 每月活跃开发者
    monthly_active = (
        df.groupby("month_date")["author"].nunique().rename("active_authors")
    )
    # 新增开发者（当月首次提交）
    author_first_commit = df.groupby("author")["month_date"].min()
    new_authors = (
        author_first_commit.value_counts().sort_index().rename("new_authors")
    )

    trend_df = pd.DataFrame(index=monthly_active.index)
    trend_df = trend_df.join(new_authors).fillna(0)
    trend_df["cumulative_authors"] = trend_df["new_authors"].cumsum()
    trend_df = trend_df.join(monthly_active).fillna(0)

    return trend_df.astype(int)


# ---------------------------------------------------------------------------
# Author stats
# ---------------------------------------------------------------------------

def compute_author_stats(
    df: pd.DataFrame,
    ref_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """计算作者维度的详细统计信息。"""
    if df.empty:
        return pd.DataFrame()

    if ref_date is None:
        ref_date = pd.Timestamp.now(tz=TARGET_TZ)

    # 基础聚合
    agg_dict: dict[str, Any] = {
        "total_commits": ("datetime_str", "count"),
        "first_commit": ("local_time", "min"),
        "last_commit": ("local_time", "max"),
        "night_commits": ("time_in_6am_day", lambda x: int((x >= 20.0).sum())),
    }
    # 如果 df 中有 insertions / deletions 列，也聚合
    if "insertions" in df.columns:
        agg_dict["total_insertions"] = ("insertions", "sum")
        agg_dict["total_deletions"] = ("deletions", "sum")

    stats = df.groupby("author").agg(**agg_dict)

    # 衍生指标
    stats["maintenance_days"] = (
        (stats["last_commit"] - stats["first_commit"]).dt.days
    )

    # 活跃判定 (近 180 天)
    days_since_last = (
        ref_date - stats["last_commit"].dt.tz_localize(ref_date.tz)
    ).dt.days
    stats["is_active"] = days_since_last <= 180

    # 参与阶段
    def _get_phase(days: int) -> str:
        if days <= 90:
            return "近期参与"
        elif days <= 365:
            return "中期参与"
        return "历史参与"

    stats["phase"] = days_since_last.apply(_get_phase)

    # 贡献程度
    stats["rank_pct"] = stats["total_commits"].rank(pct=True)

    def _get_contribution_level(pct: float) -> str:
        if pct > 0.8:
            return "核心贡献者"
        elif pct > 0.2:
            return "常规贡献者"
        return "偶尔贡献者"

    stats["contribution_level"] = stats["rank_pct"].apply(_get_contribution_level)

    # 夜间提交占比
    stats["night_ratio"] = stats["night_commits"] / stats["total_commits"]

    # Email (取最后一次使用的)
    if "email" in df.columns:
        email_map = df.groupby("author")["email"].last()
        stats = stats.join(email_map)

    return stats.sort_values("total_commits", ascending=False)


# ---------------------------------------------------------------------------
# Daily commits (for calendar heatmap)
# ---------------------------------------------------------------------------

def compute_daily_commits(df: pd.DataFrame) -> pd.Series:
    """按 date_6am_cutoff 聚合每日提交数。"""
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("date_6am_cutoff").size().sort_index()


# ---------------------------------------------------------------------------
# Code activity (monthly insertions/deletions)
# ---------------------------------------------------------------------------

def compute_code_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    按月聚合代码行数变更趋势。

    Returns DataFrame with columns:
        commits, insertions, deletions, net_lines
    """
    if df.empty or "insertions" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["month_date"] = (
        pd.to_datetime(df["date_6am_cutoff"])
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    activity = df.groupby("month_date").agg(
        commits=("hash", "nunique"),
        insertions=("insertions", "sum"),
        deletions=("deletions", "sum"),
    )
    activity["net_lines"] = activity["insertions"] - activity["deletions"]

    return activity


# ---------------------------------------------------------------------------
# File modification heatmap (for sunburst)
# ---------------------------------------------------------------------------

def compute_file_heatmap(
    file_stats_df: pd.DataFrame,
    commits_df: Optional[pd.DataFrame] = None,
    max_depth: int = 4,
) -> list[dict]:
    """
    按目录层级聚合文件修改次数，生成旭日图数据结构。

    Returns:
        嵌套字典列表 [{"name": "src", "children": [...], "value": N}, ...]
    """
    if file_stats_df.empty:
        return []

    # 统计每个文件被修改的次数（出现在多少次提交中）
    file_counts = file_stats_df.groupby("filepath").agg(
        mod_count=("hash", "nunique"),
        total_changes=("insertions", "sum"),
    )
    file_counts["total_changes"] += file_stats_df.groupby("filepath")["deletions"].sum()

    # Limit to top 100 files by modification count for performance
    file_counts = file_counts.sort_values("mod_count", ascending=False).head(50)

    # 构建树结构
    root_children: dict[str, Any] = {}

    for filepath, row in file_counts.iterrows():
        parts = str(filepath).replace("\\", "/").split("/")
        # 限制深度
        if len(parts) > max_depth:
            parts = parts[: max_depth - 1] + ["/".join(parts[max_depth - 1 :])]

        current = root_children
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {"_children": {}, "_value": 0}
            current[part]["_value"] += int(row["mod_count"])
            if i < len(parts) - 1:
                current = current[part]["_children"]

    def _build_tree(node_dict: dict) -> list[dict]:
        result = []
        for name, info in node_dict.items():
            entry: dict[str, Any] = {"name": name}
            children = _build_tree(info["_children"])
            if children:
                entry["children"] = children
            else:
                entry["value"] = info["_value"]
            result.append(entry)
        # 按 value / 子节点总 value 降序排列
        result.sort(key=lambda x: x.get("value", 0), reverse=True)
        return result

    return _build_tree(root_children)


# ---------------------------------------------------------------------------
# Code stability analysis
# ---------------------------------------------------------------------------

def compute_code_stability(df: pd.DataFrame) -> pd.DataFrame:
    """
    分析各季度的代码稳定性。

    按季度聚合:
      - insertions, deletions
      - ratio = insertions / (insertions + deletions)
      - phase: 功能开发期 / 重构期 / 稳定期
    """
    if df.empty or "insertions" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["quarter"] = (
        pd.to_datetime(df["date_6am_cutoff"])
        .dt.to_period("Q")
        .dt.to_timestamp()
    )

    stability = df.groupby("quarter").agg(
        insertions=("insertions", "sum"),
        deletions=("deletions", "sum"),
        commits=("hash", "nunique"),
    )

    total = stability["insertions"] + stability["deletions"]
    stability["add_ratio"] = (stability["insertions"] / total.replace(0, 1)).round(3)

    def _classify(ratio: float) -> str:
        if ratio >= 0.7:
            return "功能开发期"
        elif ratio <= 0.4:
            return "重构期"
        return "稳定期"

    stability["phase"] = stability["add_ratio"].apply(_classify)

    return stability


# ---------------------------------------------------------------------------
# Insights aggregation
# ---------------------------------------------------------------------------

def compute_insights(
    df: pd.DataFrame,
    file_stats_df: Optional[pd.DataFrame] = None,
) -> Dict[str, object]:
    """汇总核心指标与统计，供图表层和仪表板使用。"""
    if df.empty:
        return {}

    now_time = pd.Timestamp.now(tz=TARGET_TZ)

    total_commits = len(df)
    total_authors = df["author"].nunique()

    date_range = (
        f"{df['date_6am_cutoff'].min()} ~ {df['date_6am_cutoff'].max()}"
    )

    first_commit_date = df["date_6am_cutoff"].min()
    last_commit_date = df["date_6am_cutoff"].max()
    project_lifecycle_days = (last_commit_date - first_commit_date).days if first_commit_date and last_commit_date else 0

    # 代码行数
    net_lines = 0
    total_insertions = 0
    total_deletions = 0
    if "insertions" in df.columns:
        total_insertions = int(df["insertions"].sum())
        total_deletions = int(df["deletions"].sum())
        net_lines = total_insertions - total_deletions

    # 高级统计
    # 高级统计
    with tqdm(total=6, desc="Computing metrics", unit="step") as pbar:
        monthly_trends = compute_monthly_trends(df)
        pbar.update(1)
        
        author_stats = compute_author_stats(df, ref_date=now_time)
        pbar.update(1)
        
        daily_commits = compute_daily_commits(df)
        pbar.update(1)
        
        code_activity = compute_code_activity(df)
        pbar.update(1)
        
        code_stability = compute_code_stability(df)
        pbar.update(1)

        # 文件热度
        file_heatmap: list[dict] = []
        if file_stats_df is not None and not file_stats_df.empty:
            file_heatmap = compute_file_heatmap(file_stats_df)
        pbar.update(1)

    # 活跃人数
    active_authors_6m = 0
    if not author_stats.empty:
        active_authors_6m = int(author_stats["is_active"].sum())

    return {
        # KPI
        "total_commits": total_commits,
        "total_authors": total_authors,
        "active_authors_6m": active_authors_6m,
        "net_lines": net_lines,
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "project_lifecycle_days": project_lifecycle_days,
        "date_range": date_range,
        "first_commit_date": str(first_commit_date),
        "last_commit_date": str(last_commit_date),
        # Data
        "monthly_trends": monthly_trends,
        "author_stats": author_stats,
        "daily_commits": daily_commits,
        "code_activity": code_activity,
        "code_stability": code_stability,
        "file_heatmap": file_heatmap,
        # Raw df for developer detail panel
        "prepared_df": df,
    }
