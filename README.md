# GitInsight

GitRepository Analysis and Visualization Tool / Git 仓库分析与可视化工具

<!-- PROJECT SHIELDS -->

[![MIT License][license-shield]][license-url]

[![Python Version][python-version]][python-version]

---

<!-- PROJECT LOGO -->
<br />

<p align="center">
  <h3 align="center">GitInsight</h3>
  <p align="center">
    一款强大的 Git 仓库数据分析与可视化工具！
    <br />
    <a href="https://github.com/ryan/gitinsight"><strong>探索本项目的文档 »</strong></a>
    <br />
    <br />
    <a href="https://github.com/ryan/gitinsight">查看Demo</a>
    ·
    <a href="https://github.com/ryan/gitinsight/issues">报告Bug</a>
    ·
    <a href="https://github.com/ryan/gitinsight/issues">提出新特性</a>
  </p>

</p>

本篇README.md面向开发者

## 目录

- [GitInsight](#gitinsight)
	- [目录](#目录)
		- [上手指南](#上手指南)
					- [开发前的配置要求](#开发前的配置要求)
					- [**安装步骤**](#安装步骤)
		- [文件目录说明](#文件目录说明)
		- [开发的架构](#开发的架构)
		- [部署](#部署)
		- [使用到的框架](#使用到的框架)
		- [贡献者](#贡献者)
			- [如何参与开源项目](#如何参与开源项目)

### 上手指南

###### 开发前的配置要求

1. Python >= 3.12
2. uv (推荐使用 uv 进行包管理) 或 pip

###### **安装步骤**

1. Clone the repo

```sh
git clone https://github.com/ryan/gitinsight.git
cd GitInsight
```

2. Install dependencies

```sh
# Using uv (Recommended)
uv sync

# Or using pip
pip install .
```

3. Run the tool

```sh
# Run as module
python -m gitinsight

# Or if installed inside a virtual environment via uv/pip
gitinsight
```

### 文件目录说明

```
GitInsight
├── .github/             # GitHub 配置
├── gitinsight/          # 源代码目录
│   ├── __init__.py
│   ├── __main__.py      # 程序入口
│   ├── analysis.py      # 分析逻辑 (Pandas)
│   ├── charts.py        # 图表绘制 (Pyecharts)
│   ├── dashboard.py     # 仪表盘展示
│   ├── git_reader.py    # Git日志读取
│   └── report.py        # 报告生成
├── .gitignore
├── pyproject.toml       # 项目配置与依赖
├── uv.lock              # 依赖锁定文件
└── README.md            # 项目说明
```

### 开发的架构

本项目主要由数据读取、数据分析、图表生成和仪表盘展示四个部分组成。
- `git_reader.py`: 负责读取 Git 仓库的提交日志。
- `analysis.py`: 使用 Pandas 对日志数据进行清洗和统计分析。
- `charts.py`: 使用 Pyecharts 生成各类可视化图表。
- `dashboard.py`: 整合图表生成 HTML 仪表盘。

请阅读架构文档(如有)查阅为该项目的架构。

### 部署

本项目为 Python 命令行工具，可直接本地运行或打包发布到 PyPI。
暂无特殊部署部署。

### 使用到的框架

- [Pandas](https://pandas.pydata.org/) - Data structures and analysis tools
- [Pyecharts](https://github.com/pyecharts/pyecharts) - Python Echarts Plotting Library
- [Loguru](https://github.com/Delgan/loguru) - Python logging made (stupidly) simple
- [Hatchling](https://hatch.pypa.io/latest/) - Modern, extensible Python build backend

### 贡献者

请阅读**CONTRIBUTING.md** 查阅为该项目做出贡献的开发者。

#### 如何参与开源项目

贡献使开源社区成为一个学习、激励和创造的绝佳场所。你所作的任何贡献都是**非常感谢**的。

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- links -->
[license-shield]: https://img.shields.io/github/license/shaojintian/Best_README_template.svg?style=flat-square
[license-url]: https://github.com/ryan/gitinsight/blob/main/LICENSE
[python-version]:https://img.shields.io/pypi/pyversions/pandas
