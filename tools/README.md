# 仓库维护工具

`check_public_tree.py` 检查当前 Git 暂存区，阻止具体工程、媒体、歌词字幕、模型和运行文件进入公共仓库。它只使用 Python 标准库与 Git，无需安装项目依赖。

```bash
python tools/check_public_tree.py
python tools/check_public_tree.py --repo /path/to/repository
```

退出码：`0` 通过，`1` 不符合发布目录策略，`2` 无法读取 Git 暂存区。检查失败时只输出路径与规则，不输出文件内容。

先暂存，再检查，再审阅差异并提交。此工具不是内容或密钥扫描器；完整规则与局限见[目录与提交边界](../docs/repository-layout.md)。旧歌曲专用导入脚本仅作为本地历史恢复工具保留，不再进入 Git。
