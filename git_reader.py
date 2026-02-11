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


def get_git_log(git_dir: str) -> Optional[str]:
    """在指定 Git 目录中执行 git log 命令并返回输出文本。"""
    if not os.path.exists(git_dir):
        logger.error(f"❌ 错误：目录 '{git_dir}' 不存在。")
        return None

    try:
        result = subprocess.run(
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
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        logger.error("❌ 错误：未找到 'git' 命令。请确保 Git 已安装并添加到 PATH。")
        return None

    if result.returncode != 0:
        logger.error(f"❌ Git 命令执行失败：{result.stderr}")
        logger.error(f"   仓库路径：{os.path.abspath(git_dir)}")
        logger.error("   请确认这是一个有效的 Git 仓库。")
        return None

    return result.stdout


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

    for block in tqdm(blocks, desc="Parsing commits", unit="commit", leave=False):
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
        columns=["hash", "author", "email", "datetime_str", "message", "insertions", "deletions"],
    )
    file_stats_df = pd.DataFrame(
        file_stats,
        columns=["hash", "filepath", "insertions", "deletions"],
    )

    return commits_df, file_stats_df
