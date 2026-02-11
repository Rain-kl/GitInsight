# 项目速览
- 这是一个本地 Git 仓库分析工具：`main.py` 负责入口、日志与进度输出；分析链路为 `git_reader.py -> analysis.py -> charts.py -> dashboard.py -> report.py`。
- 输出物是可视化仪表板 HTML：`git_analysis_<repo_name>.html`，由 `dashboard.py` 拼装图表与 KPI 卡片。
- Git 日志通过 `git_reader.get_git_log()` 读取，并缓存到 `git_reader.py` 同级的 `.cache/.git_log_<hash>.cache`（默认 1 天有效）。

# 关键数据流与结构
- `git_reader.parse_git_log()` 产出两个 DataFrame：
  - `commits_df`：`hash/author/email/datetime_str/message/insertions/deletions`
  - `file_stats_df`：`hash/filepath/insertions/deletions`
- `analysis.prepare_dataframe()` 统一处理时区（`Asia/Shanghai`）并添加字段：`local_time/date/date_6am_cutoff/time_in_6am_day`；凌晨提交以 06:00 作为分界。
- `analysis.filter_automated_commits()` 按 `datetime_str` 以 `+0000` 结尾过滤自动化提交（先过滤后计算指标）。
- `analysis.compute_insights()` 聚合所有指标并返回给 `dashboard.build_dashboard_html()`，包括 `author_stats`、`monthly_trends`、`daily_commits`、`code_activity`、`code_stability`、`file_heatmap` 等。

# 图表与仪表板约定
- 图表构建集中在 `charts.py`，仪表板布局 + JS 交互在 `dashboard.py`。
- `dashboard._render_chart_div()` 会解析 pyecharts 生成的 HTML 片段并嵌入页面；`devData`/雷达图/日历图等开发者面板数据在服务端预计算。
- ECharts 资源通过 CDN 引入（`https://assets.pyecharts.org/assets/v5/echarts.min.js`）。

# 常用开发/运行方式
- 依赖由 `pyproject.toml` 管理（`uv sync`）；入口脚本为 `python main.py <git_repo_path>`，或运行后交互输入路径（见 `README.md`）。
- Windows 控制台编码已在 `main.py` 中处理（`sys.stdout`/`stderr` UTF-8 包装），保持此模式以支持中文/emoji 输出。

# 贡献时的约定与示例
- 新增指标请在 `analysis.py` 中计算并在 `compute_insights()` 中返回，再在 `charts.py`/`dashboard.py` 中渲染。
- 新图表优先复用 `charts.py` 的现有风格（`pyecharts` + 统一尺寸 + `opts` 配置）。
- 若需复用作者维度统计，参考 `compute_author_stats()` 的字段：`is_active/phase/contribution_level/night_ratio`。
