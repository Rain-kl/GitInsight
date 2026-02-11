import io
import os
import subprocess
import pandas as pd


def get_git_log(git_dir: str) -> str | None:
    """在指定Git目录中执行git log命令并返回输出文本。"""
    if not os.path.exists(git_dir):
        print(f"❌ 错误：目录 '{git_dir}' 不存在。")
        return None

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                git_dir,
                "log",
                "--pretty=format:%ad,%an",
                "--date=iso",
                "--no-color",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("❌ 错误：未找到 'git' 命令。请确保Git已安装并添加到PATH。")
        return None

    if result.returncode != 0:
        print(f"❌ Git 命令执行失败：{result.stderr}")
        print(f"   仓库路径：{os.path.abspath(git_dir)}")
        print("   请确认这是一个有效的Git仓库。")
        return None

    return result.stdout


def parse_git_log(stdout: str) -> pd.DataFrame:
    """将 git log 输出解析为 DataFrame。"""
    data = io.StringIO(stdout)
    return pd.read_csv(data, names=["datetime_str", "author"], on_bad_lines="skip")
