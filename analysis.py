from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict

import pandas as pd

TARGET_TZ = "Asia/Shanghai"


@dataclass(frozen=True)
class FilterStats:
    before: int
    removed: int
    after: int


def get_adjusted_time_in_6am_day(timestamp: pd.Timestamp) -> float:
    """
    以 06:00 为一天分界，返回调整后的时间（小时+分钟的小数）
    例如：
      00:00 -> 24.0
      05:59 -> 29.983
      06:00 -> 6.0
      23:59 -> 23.983
    """
    hour = timestamp.hour
    minute = timestamp.minute
    second = timestamp.second

    if hour < 6:
        adjusted_hour = hour + 24
    else:
        adjusted_hour = hour

    return adjusted_hour + minute / 60.0 + second / 3600.0


def get_commit_date_with_6am_cutoff(timestamp: pd.Timestamp) -> pd.Timestamp:
    """以 06:00 为分界点，凌晨提交算作前一天。"""
    if timestamp.hour < 6:
        return (timestamp - timedelta(days=1)).date()
    return timestamp.date()


def filter_automated_commits(df: pd.DataFrame) -> tuple[pd.DataFrame, FilterStats]:
    """过滤时区为 +0000 的自动化提交。"""
    before = len(df)

    def is_automated(datetime_str: str) -> bool:
        if pd.isna(datetime_str):
            return True
        return str(datetime_str).strip().endswith("+0000")

    filtered = df[~df["datetime_str"].apply(is_automated)].copy()
    after = len(filtered)
    return filtered, FilterStats(before=before, removed=before - after, after=after)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """解析时间并补充分析所需字段。"""
    df["datetime_utc"] = pd.to_datetime(
        df["datetime_str"],
        format="%Y-%m-%d %H:%M:%S %z",
        utc=True,
        errors="coerce",
    )

    df = df.dropna(subset=["datetime_utc"]).copy()
    if df.empty:
        return df

    df["local_time"] = df["datetime_utc"].dt.tz_convert(TARGET_TZ).dt.tz_localize(None)
    df["hour"] = df["local_time"].dt.hour
    df["minute"] = df["local_time"].dt.minute
    df["second"] = df["local_time"].dt.second
    df["date"] = df["local_time"].dt.date
    df["adjusted_time"] = df["local_time"].apply(get_adjusted_time_in_6am_day)
    df["date_6am_cutoff"] = df["local_time"].apply(get_commit_date_with_6am_cutoff)
    df["time_in_6am_day"] = df["adjusted_time"]

    return df


def compute_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """计算每月的人员变动趋势。"""
    if df.empty:
        return pd.DataFrame()

    # 按月重采样
    # 确保使用 date_6am_cutoff 来归组月份，保持统计口径一致
    df = df.copy()
    df["month_date"] = pd.to_datetime(df["date_6am_cutoff"]).dt.to_period("M").dt.to_timestamp()
    
    # 1. 每月活跃开发者（当月有提交）
    monthly_active = df.groupby("month_date")["author"].nunique().rename("active_authors")

    # 2. 新增开发者（当月首次提交）
    author_first_commit = df.groupby("author")["month_date"].min()
    new_authors = author_first_commit.value_counts().sort_index().rename("new_authors")

    # 3. 累计开发者
    #由于new_authors索引是月份，可能不连续，需要重新索引填充0
    trend_df = pd.DataFrame(index=monthly_active.index)
    trend_df = trend_df.join(new_authors).fillna(0)
    trend_df["cumulative_authors"] = trend_df["new_authors"].cumsum()
    trend_df = trend_df.join(monthly_active).fillna(0)

    # 转换列为int
    return trend_df.astype(int)


def compute_author_stats(df: pd.DataFrame, ref_date: pd.Timestamp = None) -> pd.DataFrame:
    """计算作者维度的详细统计信息。"""
    if df.empty:
        return pd.DataFrame()

    if ref_date is None:
        ref_date = pd.Timestamp.now(tz=TARGET_TZ)
    
    # 基础聚合
    stats = df.groupby("author").agg(
        total_commits=("datetime_str", "count"),
        first_commit=("local_time", "min"),
        last_commit=("local_time", "max"),
        # 夜间提交: adjusted_time >= 20.0 (20:00 - 06:00 次日)
        night_commits=("time_in_6am_day", lambda x: (x >= 20.0).sum())
    )

    # 计算衍生指标
    stats["maintenance_days"] = (stats["last_commit"] - stats["first_commit"]).dt.days
    
    # 活跃判定 (近180天)
    #以最后一次提交时间为参考（针对已停止维护的项目可能更合理），还是以当前时间？
    #需求文档 3.1.2: 活跃开发者 = (当前日期 - 最后提交日期) <= 180天
    #这里使用传入的 ref_date (通常是 now)
    days_since_last = (ref_date - stats["last_commit"].dt.tz_localize(ref_date.tz)).dt.days
    stats["is_active"] = days_since_last <= 180

    # 参与阶段 (Based on last commit)
    # 近期参与 (近3个月), 中期 (3-12个月), 历史 (>1年)
    def get_phase(days):
        if days <= 90: return "近期参与" 
        elif days <= 365: return "中期参与"
        else: return "历史参与"
    stats["phase"] = days_since_last.apply(get_phase)

    # 贡献程度 (按总提交数分位)
    # 核心 (Top 20%), 常规 (Bot 20-80%), 偶尔 (Bot 20%)
    # 简单的按 rank 划分
    stats["rank_pct"] = stats["total_commits"].rank(pct=True)
    def get_contribution_level(pct):
        if pct > 0.8: return "核心贡献者"
        elif pct > 0.2: return "常规贡献者"
        else: return "偶尔贡献者"
    stats["contribution_level"] = stats["rank_pct"].apply(get_contribution_level)

    # 夜间提交占比
    stats["night_ratio"] = stats["night_commits"] / stats["total_commits"]

    return stats.sort_values("total_commits", ascending=False)


def compute_insights(df: pd.DataFrame) -> Dict[str, object]:
    """汇总核心指标与统计。"""
    total_commits = len(df)
    total_authors = df["author"].nunique()

    reference_time = df["local_time"].max()
    now_time = pd.Timestamp.now(tz=TARGET_TZ)
    
    if pd.isna(reference_time):
        reference_time = now_time

    date_range = (
        f"{df['date_6am_cutoff'].min()} ~ {df['date_6am_cutoff'].max()}"
        if not df.empty
        else "无"
    )

    # 计算高级统计
    monthly_trends = compute_monthly_trends(df)
    author_stats = compute_author_stats(df, ref_date=now_time)

    # 简单的文本摘要统计
    active_recent_2m = 0
    inactive_1y = 0
    if not author_stats.empty:
        # 近2个月活跃 (约60天)
        since_last = (now_time - author_stats["last_commit"].dt.tz_localize(now_time.tz)).dt.days
        active_recent_2m = (since_last <= 60).sum()
        inactive_1y = (since_last > 365).sum()

    return {
        "total_commits": total_commits,
        "total_authors": total_authors,
        "date_range": date_range,
        "active_recent_2m": active_recent_2m,
        "inactive_1y": inactive_1y,
        "monthly_trends": monthly_trends,
        "author_stats": author_stats,
    }

    daily_commits = df.groupby("date_6am_cutoff").size().sort_index()

    overall_author_counts = df["author"].value_counts().head(10)

    night_df = df[df["time_in_6am_day"].between(20, 30, inclusive="left")]
    night_author_counts = night_df["author"].value_counts().head(10)

    recent_3m_df = df[df["local_time"] >= reference_time - pd.DateOffset(months=3)]
    recent_3m_counts = recent_3m_df["author"].value_counts().head(10)

    last_commit_by_author = df.groupby("author")["local_time"].max()
    active_recent_2m = int((last_commit_by_author >= reference_time - pd.DateOffset(months=2)).sum())
    inactive_1y = int((last_commit_by_author < reference_time - pd.DateOffset(years=1)).sum())

    metrics = {
        "total_commits": total_commits,
        "total_authors": total_authors,
        "date_range": date_range,
        "daily_commits": daily_commits,
        "overall_author_counts": overall_author_counts,
        "night_author_counts": night_author_counts,
        "recent_3m_author_counts": recent_3m_counts,
        "active_recent_2m": active_recent_2m,
        "inactive_1y": inactive_1y,
    }

    return metrics
