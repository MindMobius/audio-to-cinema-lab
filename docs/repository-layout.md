# 目录与提交边界

工程按内容职责组织，`projects/` 是日常制作的唯一入口。代码、当前工程和常用素材放在 C 盘 NVMe；`D:\AI-Archive` 只保存冷归档。

```text
source/music/                  原始音乐与 LRC，仅本地
library/music/                 共享音乐目录、解码结果、歌词版本，仅本地
projects/YYYY-MM-DD/<slug>/     每支 MV 的全部工程，仅本地
src/cinema_lab/                 CLI 与可执行实现
  resources/
    schemas/                   通用数据契约
    recipes/                   制作配方
    templates/production/      空白模板
docs/                          架构、工具、流程和制作经验
tests/                         合成数据测试
tools/                         仓库维护与提交检查
.github/                       CI 与贡献模板
```

日期表示工程创建日期，后续渲染使用 revision。默认 `cinema-lab init` 写入 `projects/`，拒绝覆盖同名工程。歌曲从[音乐资产库](music-library.md)选择并锁定；媒体、歌词、提示词、工作流、字幕、生成回执、交付视频全部留本地。

当前工作区不提供旧目录布局、隐藏别名或兼容链接。每个活动工程只使用一个明确路径：

```text
C:\AI\projects\audio-to-cinema-lab\projects\YYYY-MM-DD\<slug>\
```

历史大文件和已完成资产需要长期保留时，移动到 `D:\AI-Archive`；恢复使用时再显式提升回 C 盘活动工作区。

参见[当前决策](decisions/2026-11-11-music-library-and-projects.md)。

## 提交前检查

```powershell
python tools/check_public_tree.py
git diff --cached --check
git diff --cached --stat
```

先暂存公共代码与文档，再检查和审阅差异。脚本检查 Git 暂存区，拒绝 `source/`、`library/`、`projects/` 等本地数据目录、媒体/歌词/模型/压缩包、具体工程清单、符号链接和超过 1 MiB 的文件。强制添加也会被检查拦下，CI 在 Windows runner 上执行相同策略。
