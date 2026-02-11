import sys
from pathlib import Path

from analysis import compute_insights, filter_automated_commits, prepare_dataframe
from charts import render_charts
from git_reader import get_git_log, parse_git_log
from report import export_csv, print_summary


def resolve_git_dir() -> str | None:
    if len(sys.argv) > 1:
        return sys.argv[1]

    git_dir = input("请输入Git仓库目录路径: ").strip()
    if not git_dir:
        print("❌ 未指定Git仓库目录。")
        print("使用方法: python main.py [git_repo_directory]")
        print("或直接运行脚本并在提示时输入目录路径。")
        return None
    return git_dir


def main() -> None:
    git_dir = resolve_git_dir()
    if not git_dir:
        return

    stdout = get_git_log(git_dir)
    if stdout is None:
        sys.exit(1)

    if not stdout.strip():
        print("⚠️ 当前仓库没有提交记录。")
        return

    df_raw = parse_git_log(stdout)
    if df_raw.empty:
        print("❌ 无法读取任何有效提交记录。")
        return

    df_filtered, filter_stats = filter_automated_commits(df_raw)
    if df_filtered.empty:
        print("⚠️ 过滤后没有有效的人工提交记录。")
        return

    df_prepared = prepare_dataframe(df_filtered)
    if df_prepared.empty:
        print("❌ 所有提交时间都无法解析。")
        return

    metrics = compute_insights(df_prepared)

    repo_name = Path(git_dir).resolve().name or "git_repo"
    output_csv = f"git_dev_insights_report_{repo_name}.csv"
    output_html = f"git_dev_insights_charts_{repo_name}.html"

    export_csv(output_csv, metrics)
    render_charts(metrics, output_html)

    print_summary(
        metrics,
        filter_stats,
        {"csv": output_csv, "html": output_html},
    )

if __name__ == "__main__":
    main()