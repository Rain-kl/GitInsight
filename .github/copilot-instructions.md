# Copilot instructions

## 项目概览
- 目标：读取目标 Git 仓库提交记录（`git log --date=iso`），过滤自动化提交（时间字符串以 `+0000` 结尾），按 **Asia/Shanghai** 时区分析，并以 **06:00** 为一天分界生成开发者洞察。
- 产出：当前工作目录生成 `git_dev_insights_report_<repo_name>.csv` 与 `git_dev_insights_charts_<repo_name>.html`。

## 架构与数据流（跨文件）
- `main.py` 负责 CLI/交互入口：解析路径 → `git_reader.get_git_log()` → `parse_git_log()` → `analysis.filter_automated_commits()` → `prepare_dataframe()` → `compute_insights()` → `report.export_csv()` + `charts.render_charts()` + `report.print_summary()`。
- `git_reader.py` 只做 Git 读取与日志解析，输出包含 `datetime_str, author` 的 DataFrame。
- `analysis.py` 负责所有时间逻辑与统计：
  - `get_adjusted_time_in_6am_day()` / `get_commit_date_with_6am_cutoff()` 把 0:00-5:59 归入前一天。
  - `time_in_6am_day` 是跨日统计的统一字段；不要直接用 `hour` 做跨日判断。
- `report.py` 固定 CSV 字段顺序与中文文案；`charts.py` 用 `pyecharts` 生成 HTML 图表。

## 关键约定与模式
- 时间解析必须使用 `pd.to_datetime(..., format='%Y-%m-%d %H:%M:%S %z', utc=True)`，再 `tz_convert('Asia/Shanghai')`（见 `prepare_dataframe()`）。
- 自动化提交过滤规则：`datetime_str` 以 `+0000` 结尾即视为自动化（`filter_automated_commits()`）。
- 晚间分段固定为 `18:00-19:00` / `19:00-20:00` / `20:00-次日06:00`，以 `PERIOD_ORDER` 为准。

## 开发/运行流程
- 依赖由 `pyproject.toml` 管理（Python >= 3.12，`pandas` + `pyecharts`）。
- 运行入口：`uv run main.py /path/to/git/repo` 或直接运行后按提示输入路径（见 `README.md`）。

## 修改注意事项（保持统计一致）
- 若调整时间段或分界逻辑，需同步修改：`PERIOD_ORDER`、`calculate_time_period_stats()`、`report.export_csv()` 的字段顺序与含义。
- 新增指标需同步更新 `report.print_summary()` 的输出文案，并确认图表是否需要补充。
