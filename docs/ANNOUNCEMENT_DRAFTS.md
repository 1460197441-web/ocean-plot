# 发布文案草稿

以下文案尚未发布到群聊、知乎、小红书或 Pangeo。先核实渠道规则，再选择适合的一处发布；不要复制到无关问题下面，不索要互 Star。

## 同学群 / 课题组

把常用的海洋 NetCDF 绘图流程整理开源了：ocean-plot。可以命令行查看 nc、画 SST 和风场、提取单点海温序列并导出 CSV，附 OISST/CCMP 实际示例和离线 demo。适合规则经纬网的小数据制图；曲线网格、跨日界线区域等限制也写清楚了。

仓库：https://github.com/1460197441-web/ocean-plot

有类似数据可以试试，遇到变量名或单位兼容问题欢迎提 issue。配图用 README 顶部的黄海海温图。当前从 GitHub Release 安装，尚未发布 PyPI。

## 知乎 / 小红书

标题：海洋专业常用的 nc 海温 / 风场绘图，我整理成 Python 命令行工具了

经常读 OISST、CCMP 一类 nc 文件，就把查看变量、海温地图、风矢量、单点时间序列和 CSV 导出整理成了 ocean-plot，代码开源。

它做的是明确的小任务：给定文件、时间和区域，输出 PNG/PDF。不会偷偷平均额外维度、填补缺测或把合成数据当观测；不支持的网格会报错。附离线 demo 和真实产品示例，方便先试再用自己的数据。

GitHub：1460197441-web/ocean-plot。安装与局限见 README。欢迎实际使用反馈，不承诺兼容所有 nc 文件。

## Pangeo: News & Announcements

Title: ocean-plot: a small CLI for SST maps, wind vectors and point time series from NetCDF

Hi all — I'm sharing a small open-source tool I maintain, ocean-plot, built on xarray and Matplotlib, with optional Cartopy maps.

It wraps a few recurring tasks for rectilinear ocean datasets: inspecting NetCDF metadata, plotting SST and geographic wind vectors, and exporting nearest-grid-point temperature series to CSV. It has been smoke-tested with OISST and CCMP subsets, and includes an offline synthetic demo.

The emphasis is explicit selection and predictable handling of missing values. It does not silently average time/depth dimensions. Regional domains that become discontinuous at the dateline are rejected; curvilinear grids and non-standard-calendar time series are not supported yet.

Code, examples and GitHub Release downloads: https://github.com/1460197441-web/ocean-plot

I'd appreciate feedback on the CLI and metadata compatibility, especially small reproducible examples that fail. It's an early release, not a replacement for a general analysis library. PyPI publishing is not available yet.

使用本人Pangeo账号在合适的News & Announcements分类发帖；登录或版规不允许时不要换渠道刷屏。项目后续已发布PyPI时，先更新最后一句再发送。
