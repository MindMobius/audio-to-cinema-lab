# 目录与提交边界

公共仓库按照职责组织：

```text
src/cinema_lab/                 CLI 与可执行实现
  resources/
    schemas/                   通用数据契约
    recipes/                   可复制的制作配方
    templates/production/      视觉方向等空白模板
docs/
  adapters/                    各环节的工具说明与能力边界
  pipelines/                   流程编排说明
  production/                  制作手册、配方、经验与路线图
  decisions/                   目录、数据与架构决策
tests/                         使用合成数据的测试
tools/                         仓库维护与提交检查
.github/                       CI 与贡献模板
```

`docs/adapters/` 与 `docs/pipelines/` 是文档目录，不表示对应执行器已实现。可执行代码放在 `src/cinema_lab/`。包内资源随 wheel 分发，运行时不依赖仓库根目录。

## 每支作品只留本地

```text
.local/projects/YYYY-MM-DD/project-slug/
  audio/
  concept/
  assets/
  shots/
  workflows/
  edit/
  verification/
```

日期表示创建日期，工程名保持稳定，后续渲染使用 revision。`cinema-lab init` 默认写入 `.local/projects`，拒绝覆盖已有工程。

整支作品的工程均留本地，包括音频、完整歌词、图片、视频、提示词、工作流、字幕、时间线、生成回执和检查记录。登记原始文件哈希与选定版本；向 Lab 提炼时只保留通用方法、空白模板和合成测试数据。

旧版 `projects/`、歌曲专用 `tools/import_project.py` 保留在原位置并取消 Git 跟踪。原始音源 `source/`、本机第三方工具 `third_party/` 与运行产物也被忽略。不要为了目录美观移动或删除仍被旧工程引用的文件。

取消跟踪只影响后续提交，不会删除历史提交中的工程内容。本次整理不改写 Git 历史。参见[决策记录](decisions/2026-11-11-local-productions.md)。

## 提交前检查

先明确暂存需要发布的代码、文档与通用模板，再执行：

```bash
python tools/check_public_tree.py
git diff --cached --check
git diff --cached --stat
```

检查脚本读取 **Git 暂存区**，不会遍历本地工程。它拒绝工程和运行目录、常见媒体/歌词字幕/模型/压缩包、具体工程清单、符号链接/子模块、未解决的合并条目，以及超过 1 MiB 的文件。`git add -f` 不能绕过这些检查。CI 执行同一脚本；本地需主动运行，并未安装 Git hook。

这是一道结构检查，不能识别任意文件内夹带的歌曲或项目内容。仍需人工查看暂存差异；新增公共目录或确需发布的素材类型应与检查策略一起评审。`.gitignore`、结构检查和差异审查共同维护提交边界。
