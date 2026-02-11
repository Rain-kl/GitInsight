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

- 终端输出：展示提交总量、统计日期范围、活跃/不活跃人数等摘要信息。
- CSV 报告：`git_dev_insights_report_<repo_name>.csv`
- 可视化图表（pyecharts HTML）：`git_dev_insights_charts_<repo_name>.html`
	- 每日提交趋势折线图
	- Top10 总提交量排行
	- Top10 20:00-06:00 提交排行
	- Top10 最近3个月提交排行
	- 参与与活跃人数统计

