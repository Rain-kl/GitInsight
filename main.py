"""
main.py — Git 项目人员分析可视化系统入口。
"""
import io
import sys
from pathlib import Path

# Fix Windows console encoding for Chinese + emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from analysis import compute_insights, filter_automated_commits, prepare_dataframe
from dashboard import build_dashboard_html
from git_reader import get_git_log, parse_git_log
from report import print_summary


def resolve_git_dir() -> str | None:
    if len(sys.argv) > 1:
        return sys.argv[1]

    git_dir = input("请输入Git仓库目录路径: ").strip()
    if not git_dir:
        print("未指定Git仓库目录。")
        print("使用方法: python main.py [git_repo_directory]")
        return None
    return git_dir


def main() -> None:
    git_dir = resolve_git_dir()
    if not git_dir:
        return

    print("[1/5] 正在读取 Git 日志...")
    stdout = get_git_log(git_dir)
    if stdout is None:
        sys.exit(1)

    if not stdout.strip():
        print("当前仓库没有提交记录。")
        return

    print("[2/5] 正在解析提交记录...")
    commits_df, file_stats_df = parse_git_log(stdout)
    if commits_df.empty:
        print("无法读取任何有效提交记录。")
        return

    print(f"      解析到 {len(commits_df)} 条提交，{len(file_stats_df)} 条文件变更记录")

    # 过滤自动化提交
    df_filtered, filter_stats = filter_automated_commits(commits_df)
    if df_filtered.empty:
        print("过滤后没有有效的人工提交记录。")
        return

    # 准备 DataFrame（解析时间等）
    print("[3/5] 正在计算分析指标...")
    df_prepared = prepare_dataframe(df_filtered)
    if df_prepared.empty:
        print("所有提交时间都无法解析。")
        return

    # 计算所有洞察指标
    metrics = compute_insights(df_prepared, file_stats_df)

    # 生成仪表板
    repo_name = Path(git_dir).resolve().name or "git_repo"
    output_html = f"git_analysis_{repo_name}.html"

    print("[4/5] 正在生成可视化仪表板...")
    build_dashboard_html(metrics, repo_name, output_html)

    # 打印摘要
    print("[5/5] 完成!")
    print_summary(metrics, filter_stats, {"html": output_html})


if __name__ == "__main__":
    main()