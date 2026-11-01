# 本机技能导航

Python 3.10+，浏览器支持原生 dialog 和 Clipboard API。页面仅展示只读清单，不执行技能、不修改宿主状态，不加载远程字体、脚本或分析服务。

从导航目录（含 `site/` 和 `source-data/`）运行：

```sh
python3 site/serve.py --port 8765
```

打开 <http://127.0.0.1:8765/site/>。按 Ctrl+C 停止服务。不要直接以 file:// 打开页面；浏览器会限制数据读取。端口被占用时指定另一个端口。

首次使用或宿主状态变化后，先重新生成 Vibe 索引，再运行 `source-data/export_enabled_skills.py --help` 所示的导出命令，输出到 `source-data/enabled-skills.json`，指南输出到 `source-data/skills-guide.md`。清单缺失、损坏或统计不一致时，页面明确报错。

搜索支持技能 ID、名称、描述和来源标签；筛选按来源与绑定状态组合。点击结果查看元数据与可复制的入口。`/` 聚焦搜索，Esc 关闭详情，所有控件可使用键盘操作。结果按需分批显示。

`host_enabled`、`binding_status`、`dependency_status` 是不同事实。清单中的依赖状态默认未知，实际调用与交付验收由具体任务另行提供证据。

导出的真实 JSON、指南、索引、日志和含本机路径的截图属于私有本地产物，不应公开提交。
