# Audio-to-Cinema Lab

**声音驱动影像创作实验室**：从音频的文本、结构与情绪出发，设计视觉方向，建立人物和场景资产，再生成、编排和交付完整视频。

当前重心是音乐 MV。工具可以替换；流程围绕音频、意象、资产、镜头、时间线和成片组织。分析提供依据，创作决定怎样表达，技术检查与审美验收分别记录。

## 已经沉淀的内容

| 能力 | 当前状态 | 入口 |
| --- | --- | --- |
| 音乐入库、按需解码、缓存复用、工程版本锁定 | 可执行 | [音乐资产管理](docs/music-library.md) |
| 本地项目初始化、元数据校验、媒体校验与恢复 | 可执行；不等于视频生成 | `cinema-lab init / validate / media` |
| 分镜叙事、抽象情绪、连续长卷 | 三种可复制的制作配方；生成器尚未统一封装 | [制作配方](docs/production/recipes.md) |
| 风格约束、人物资产树、分层动作、字幕、片头 | 来自制作实践的模板与规范 | [MV 制作手册](docs/production/mv-playbook.md) |
| 模型、LoRA、合成与审片经验 | 项目内已有运行记录；通用执行器待提炼 | [组件状态](docs/production/components.md) |
| 返工原因、失效模式与提炼顺序 | 已整理，可持续补充 | [复盘与迭代计划](docs/production/lessons-and-roadmap.md) |

这些配方负责建立创作和审查骨架，没有提供“一条命令自动生成完整 MV”的能力。每支作品的视觉语言仍需针对歌曲设计。

## 工作流程

```text
音频母版与歌词
  → 音频观察（文本 / 结构 / 节奏 / 能量）
  → 视觉决策（情绪解释 / 风格 / 表现形式）
  → 资产树（身份 / 着装 / 姿势 / 场景 / 物件）
  → 最小样段（验证画风、动作、衔接、歌词阅读）
  → 完整生成、选片与返修
  → 后期编排（镜头 / 文字 / 片头片尾 / 完整音轨）
  → 技术检查与画面审查
  → 本地交付、通用经验回流
```

## 快速开始

在 Linux / WSL 的项目目录中执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cinema-lab init --date 2026-11-11 --slug my-mv --title "作品名称" \
  --recipe continuous-scroll
cinema-lab validate projects/2026-11-11/my-mv
```

可选配方：`cinematic-scenes`（分镜叙事）、`abstract-emotion`（抽象情绪）、`continuous-scroll`（连续长卷）。不传 `--recipe` 时创建基础空工程。

初始化会写入视觉方向模板、配方说明、字幕参考设置和审查计划。草稿可以尚未登记音频时长；离开 `planning` 状态后必须提供真实时长。校验通过只说明元数据符合约定。

管理本地音乐储备：

```bash
cinema-lab music scan
cinema-lab music list
cinema-lab music prepare "歌曲名称"
cinema-lab init --date 2026-11-11 --slug another-mv --title "作品名称" \
  --recipe abstract-emotion --music "歌曲名称"
cinema-lab music audit
```

把原始音频和同名 LRC 放进 `source/music/`。扫描不批量解码；选中歌曲时按需准备，已校验的解码结果直接复用。工程保存所选音频和歌词的独立副本与哈希，库里新增版本不会修改已有作品。音乐多版本、历史解码导入与命令详见[音乐资产管理](docs/music-library.md)。

## 目录导航

- `src/cinema_lab/`：CLI、音频输入和通用项目能力。
- `src/cinema_lab/resources/`：schema、制作配方、空白模板，随 Python 包分发。
- `docs/`：工具、流程、制作经验和架构；见[文档入口](docs/README.md)。
- `tests/`：合成数据测试；`tools/`：仓库维护与提交检查。

## 仓库与作品分开

公共 Git 仓库存放可复用代码、配方、接口、文档和合成测试数据。
**每一支具体 MV 的全部工程只留本地**，包括音频、歌词、图像、视频、提示词、工作流、字幕、生成回执及交付记录。

```text
projects/YYYY-MM-DD/project-slug/
├── audio/
├── concept/
├── assets/
├── shots/
├── workflows/
├── edit/
└── verification/
```

日期表示作品创建日期；修改通过 revision 管理。初始化拒绝覆盖同名工程。`source/`、`library/`、`projects/`、`archive/` 都被 Git 忽略。工程统一使用 `projects/`，不保留旧目录或兼容链接。旧提交中的历史不会因取消跟踪而自动消失。

详见[目录规则](docs/repository-layout.md)、[架构](docs/architecture.md)和[制作流程](docs/workflow.md)。

提交前先暂存公共文件，再运行 `python tools/check_public_tree.py` 并审阅暂存差异。CI 也会检查 Git 树，拒绝具体工程、媒体、歌词字幕和模型文件。检查范围与例外处理见[目录规则](docs/repository-layout.md)。
