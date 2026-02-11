使用方式

```
uv sync

# 方法1：通过命令行参数指定目录
python main.py /path/to/your/git/repository

# 方法2：运行脚本后输入目录
python main.py
# 然后会提示：请输入Git仓库目录路径:
```

输出说明

- 终端输出：仅展示摘要信息（提交量、最晚提交、18:00后占比、分段统计等）。
- CSV 报告：`git_dev_insights_report_<repo_name>.csv`
- 可视化图表（pyecharts HTML）：`git_dev_insights_charts_<repo_name>.html`

