"""
git_reader.py — 从 Git 仓库提取完整提交记录与文件变更统计。

输出:
  - commits_df: 每行一条提交 (hash, author, email, datetime_str, message, insertions, deletions)
  - file_stats_df: 每行一个文件变更 (hash, filepath, insertions, deletions)
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

from loguru import logger
from tqdm import tqdm

import pandas as pd

# 分隔符，用于区分每条提交
_COMMIT_SEP = "---COMMIT_BOUNDARY---"

_GIT_LOG_FORMAT = f"{_COMMIT_SEP}%n%H%n%an%n%ae%n%ad%n%s"


def _count_commits(git_dir: str) -> Optional[int]:
    """快速获取仓库的总提交数（用于进度条）。"""
    try:
        result = subprocess.run(
            ["git", "-C", git_dir, "rev-list", "--all", "--count"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (FileNotFoundError, ValueError):
        pass
    return None


def get_git_log(git_dir: str) -> Optional[str]:
    """在指定 Git 目录中执行 git log 命令并返回输出文本，同时显示进度条。"""
    import time
    import hashlib
    from pathlib import Path

    if not os.path.exists(git_dir):
        logger.error(f"❌ 错误：目录 '{git_dir}' 不存在。")
        return None

    # Determine cache file path
    git_path = Path(git_dir).resolve()
    if git_path.name == ".git":
        git_path = git_path.parent

    # Save cache to ~/.cache/gitinsight directory
    cache_dir = Path.home() / ".cache" / "gitinsight"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Use hash of the absolute path to generate unique cache filename
    repo_hash = hashlib.md5(str(git_path).encode("utf-8")).hexdigest()[:12]
    cache_path = cache_dir / f".git_log_{repo_hash}.cache"

    # Check cache validity (1 day = 86400 seconds)
    if cache_path.exists():
        try:
            mtime = cache_path.stat().st_mtime
            if time.time() - mtime < 86400:
                logger.info("✅ 发现有效的 Git 日志缓存，直接读取...")
                with open(cache_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                logger.info("ℹ️ Git 日志缓存已过期，正在重新读取...")
        except Exception as e:
            logger.warning(f"⚠️ 读取缓存失败: {e}")

    # 先获取总提交数，用于进度条
    total_commits = _count_commits(git_dir)

    try:
        proc = subprocess.Popen(
            [
                "git",
                "-C",
                git_dir,
                "log",
                "--all",
                f"--pretty=format:{_GIT_LOG_FORMAT}",
                "--date=iso",
                "--numstat",
                "--no-color",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        logger.error("❌ 错误：未找到 'git' 命令。请确保 Git 已安装并添加到 PATH。")
        return None

    # 逐行读取，遇到 COMMIT_SEP 时更新进度
    lines: list[str] = []
    with tqdm(
        total=total_commits, desc="正在读取 Git 日志", unit="commit", leave=False
    ) as pbar:
        for line in proc.stdout:  # type: ignore[union-attr]
            lines.append(line)
            if _COMMIT_SEP in line:
                pbar.update(1)

    stderr_output = proc.stderr.read() if proc.stderr else ""  # type: ignore[union-attr]
    proc.wait()

    if proc.returncode != 0:
        logger.error(f"❌ Git 命令执行失败：{stderr_output}")
        logger.error(f"   仓库路径：{os.path.abspath(git_dir)}")
        logger.error("   请确认这是一个有效的 Git 仓库。")
        return None

    result = "".join(lines)

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(result)
        logger.info(f"✅ Git 日志已缓存至: {cache_path}")
    except Exception as e:
        logger.warning(f"⚠️ 写入缓存失败: {e}")

    return result


# numstat 行的正则: <insertions>\t<deletions>\t<filepath>
# 二进制文件显示为 -\t-\tfilepath
_NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")


def parse_git_log(stdout: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    将 git log --numstat 输出解析为两个 DataFrame。

    Returns:
        commits_df: 每条提交一行
        file_stats_df: 每个文件变更一行
    """
    commits: list[dict] = []
    file_stats: list[dict] = []

    blocks = stdout.split(_COMMIT_SEP)

    for block in tqdm(blocks, desc="正在解析提交记录", unit="commit", leave=False):
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        # 前5行: hash, author, email, date, message
        if len(lines) < 5:
            continue

        commit_hash = lines[0].strip()
        author = lines[1].strip()
        email = lines[2].strip()
        datetime_str = lines[3].strip()
        message = lines[4].strip()

        total_ins = 0
        total_del = 0

        # 从第5行开始是 numstat（可能有空行间隔）
        for i in range(5, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            m = _NUMSTAT_RE.match(line)
            if m:
                ins_str, del_str, filepath = m.groups()
                ins = int(ins_str) if ins_str != "-" else 0
                dels = int(del_str) if del_str != "-" else 0
                total_ins += ins
                total_del += dels
                file_stats.append(
                    {
                        "hash": commit_hash,
                        "filepath": filepath,
                        "insertions": ins,
                        "deletions": dels,
                    }
                )

        commits.append(
            {
                "hash": commit_hash,
                "author": author,
                "email": email,
                "datetime_str": datetime_str,
                "message": message,
                "insertions": total_ins,
                "deletions": total_del,
            }
        )

    commits_df = pd.DataFrame(
        commits,
        columns=[
            "hash",
            "author",
            "email",
            "datetime_str",
            "message",
            "insertions",
            "deletions",
        ],
    )
    file_stats_df = pd.DataFrame(
        file_stats,
        columns=["hash", "filepath", "insertions", "deletions"],
    )

    return commits_df, file_stats_df
