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


def compute_insights(df: pd.DataFrame) -> Dict[str, object]:
    """汇总核心指标与统计。"""
    total_commits = len(df)
    total_authors = df["author"].nunique()

    reference_time = df["local_time"].max()
    if pd.isna(reference_time):
        reference_time = pd.Timestamp.now()

    date_range = (
        f"{df['date_6am_cutoff'].min()} ~ {df['date_6am_cutoff'].max()}"
        if not df.empty
        else "无"
    )

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
