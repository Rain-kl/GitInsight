from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict

import pandas as pd

TARGET_TZ = "Asia/Shanghai"
PERIOD_ORDER = ["18:00-19:00", "19:00-20:00", "20:00-次日06:00"]


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


def format_time_display(timestamp: pd.Timestamp) -> str:
    """显示时间字符串，凌晨标记为次日凌晨。"""
    date_str = timestamp.date()
    if timestamp.hour < 6:
        return f"{date_str} {timestamp.hour:02d}:{timestamp.minute:02d}（次日凌晨）"
    return f"{date_str} {timestamp.hour:02d}:{timestamp.minute:02d}"


def format_time_from_adjusted(adjusted_time: float) -> str:
    hour_int = int(adjusted_time)
    minute_int = int((adjusted_time - hour_int) * 60)
    if hour_int >= 24:
        hour_int -= 24
        return f"{hour_int:02d}:{minute_int:02d}（次日凌晨）"
    return f"{hour_int:02d}:{minute_int:02d}"


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


def calculate_time_period_stats(df: pd.DataFrame) -> Dict[str, Dict[str, object]]:
    """统计晚间时间段提交分布。"""
    total_commits = len(df)
    period_stats: Dict[str, Dict[str, object]] = {
        label: {"count": 0, "percentage": 0.0, "author_counts": {}}
        for label in PERIOD_ORDER
    }

    for _, row in df.iterrows():
        hour = row["hour"]
        author = row["author"]

        if 18 <= hour < 19:
            period = "18:00-19:00"
        elif 19 <= hour < 20:
            period = "19:00-20:00"
        elif hour >= 20 or hour < 6:
            period = "20:00-次日06:00"
        else:
            continue

        stats = period_stats[period]
        stats["count"] += 1
        author_counts = stats["author_counts"]
        author_counts[author] = author_counts.get(author, 0) + 1

    for label, stats in period_stats.items():
        stats["percentage"] = (stats["count"] / total_commits * 100) if total_commits else 0.0

    return period_stats


def get_period_top_authors(period_stats: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """获取各时间段提交最多的作者。"""
    top_authors: Dict[str, Dict[str, object]] = {}
    for period, stats in period_stats.items():
        author_counts = stats["author_counts"]
        if not author_counts:
            top_authors[period] = {"author": "无", "count": 0}
            continue
        top_author = max(author_counts.items(), key=lambda item: item[1])
        top_authors[period] = {"author": top_author[0], "count": top_author[1]}
    return top_authors


def compute_insights(df: pd.DataFrame) -> tuple[Dict[str, object], Dict[str, Dict[str, object]], Dict[str, Dict[str, object]]]:
    """汇总核心指标与统计。"""
    total_commits = len(df)
    total_authors = df["author"].nunique()

    latest_time_row = df.loc[df["adjusted_time"].idxmax()]
    latest_time_display = format_time_display(latest_time_row["local_time"])
    latest_author = latest_time_row["author"]

    daily_latest = df.groupby("date_6am_cutoff")["time_in_6am_day"].max()
    median_latest_hour = daily_latest.median() if not daily_latest.empty else 0.0
    median_time_str = format_time_from_adjusted(median_latest_hour)

    after_18_df = df[df["time_in_6am_day"] >= 18]
    after_18_count = len(after_18_df)
    after_18_pct = (after_18_count / total_commits * 100) if total_commits else 0.0

    night_counts = after_18_df.groupby("author").size()
    if not night_counts.empty:
        most_night_author = night_counts.idxmax()
        most_night_count = int(night_counts.max())
    else:
        most_night_author = "无"
        most_night_count = 0

    period_stats = calculate_time_period_stats(df)
    top_authors = get_period_top_authors(period_stats)

    overall_author_counts = df["author"].value_counts().head(10)

    metrics = {
        "total_commits": total_commits,
        "total_authors": total_authors,
        "latest_time_display": latest_time_display,
        "latest_author": latest_author,
        "median_time_str": median_time_str,
        "after_18_pct": after_18_pct,
        "after_18_count": after_18_count,
        "most_night_author": most_night_author,
        "most_night_count": most_night_count,
        "overall_author_counts": overall_author_counts,
    }

    return metrics, period_stats, top_authors
