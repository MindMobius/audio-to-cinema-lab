# 目录与提交边界

工作区按内容职责组织，不再把日常工程放进 `.local/projects/`。

```text
source/music/                  原始音乐与 LRC，仅本地
library/music/                 共享音乐目录、解码结果、歌词版本，仅本地
library/legacy/                保留可追踪关系的旧共享数据，仅本地
projects/YYYY-MM-DD/<slug>/     每支 MV 的全部工程，仅本地
archive/                       迁移原件与维护记录，仅本地
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

## 旧目录迁移

```bash
cinema-lab migrate-layout
cinema-lab migrate-layout --apply
```

默认只输出计划。执行时先检查冲突和容量，复制每个文件并校验源、目标哈希，全部成功后才归档原件。不同内容的同名文件会阻止迁移，不覆盖任何一份。旧绝对路径通过 `.local/` 下的兼容链接继续有效，实际工作文件统一位于新目录；新代码和操作使用规范路径。

原件保存在 `archive/layout-<时间>/original-local/`，迁移清单记录路径、哈希及软链接映射。旧回执保留原记录，不为了改变展示路径重写历史证据。原文件归档不会主动删除下载目录中的历史交付副本。

歌曲专用旧导入脚本保留本地且不进入 Git。本机第三方工具和运行数据仍忽略。目录边界由 Git 规则与提交检查控制，不依赖隐藏目录。

参见[当前决策](decisions/2026-11-11-music-library-and-projects.md)。旧决策保留历史上下文，由此规则替代。取消跟踪不删除历史提交，本次不改写 Git 历史。

## 提交前检查

```bash
python tools/check_public_tree.py
git diff --cached --check
git diff --cached --stat
```

先暂存公共代码与文档，再检查和审阅差异。脚本检查 Git 暂存区，拒绝 `source/`、`library/`、`projects/`、`archive/`、`.local/` 等本地数据目录、媒体/歌词/模型/压缩包、具体工程清单、符号链接和超过 1 MiB 的文件。强制添加也会被检查拦下，CI 执行相同策略。

结构检查不能识别任意合法文本文件里夹带的具体作品内容；仍需审阅暂存差异。未安装本地 Git hook。
