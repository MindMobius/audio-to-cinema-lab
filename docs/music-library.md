# 音乐资产管理

音乐储备与具体 MV 分开管理。一份音源可以被多个作品引用；歌词更新或新版本入库不能悄悄改变已有作品。

## 三个日常目录

- `source/music/`：用户提供的原始音频与同名 LRC。扫描和准备不会修改、重命名或删除原文件。
- `library/music/`：本地资产目录、不可覆盖的解码音频、封面、歌词版本和回执。
- `projects/YYYY-MM-DD/<slug>/`：每支 MV 的独立工程、选定输入、图像、镜头、合成与交付文件。

三个目录全部忽略，不提交 Git。`archive/` 保存迁移原件与维护审计，`library/legacy/` 保存尚未归入通用资产结构的旧数据。它们不是新工程入口。

## 入库与选歌

```bash
cinema-lab music scan
cinema-lab music list
cinema-lab music list "歌手或歌曲名称"
cinema-lab music list --json
```

扫描以原始音频的完整 SHA-256 生成 `music-<sha256>` 资产 ID。相同字节不同文件名合并为同一资产；同名不同字节是不同音源版本。文件改名不会改变身份；来源消失也不会删除旧资产和工程锁定副本。

同名 LRC 只做配对，原样保存为按哈希区分的版本。文件配对不表示时间轴已经验收。用户确认过的 LRC 不自动偏移、重写或重新对齐。多个文件别名带来不同歌词候选时，需要显式选定版本。

`list` 显示可唯一定位的 ID 前缀、歌曲、格式、准备状态、歌词版本数和引用工程数。命令允许完整 ID、唯一 ID 前缀、完整文件名或歌曲名称；多个匹配会报错，不任意选歌。

## 只准备选中的歌曲

```bash
cinema-lab music prepare "歌曲名称"
```

- NCM：调用现有 Python 解码适配器，保留上游来源记录，输出 MP3 或 FLAC，不重新编码。
- MP3、FLAC、M4A、WAV 等：校验并复制，不经过 NCM 解码。
- 已准备：核对缓存文件哈希后复用，不重复解码。
- 新输出：用 FFprobe 验证有音频流、正时长、采样率和声道，记录哈希与处理回执。FFprobe 需由运行环境提供。
- 缓存损坏或源文件变动：明确报错，不覆盖旧版本；恢复记录对应的缓存，或扫描新的音源版本再使用。

`pending` 表示尚未准备，`ready` 表示已测量并缓存，`failed` 表示处理失败，`corrupt` 表示缓存与回执不一致。来源是否仍存在单独记录；`ready` 不代表音乐分析、歌词同步或审美验收已完成。

可导入以前的批次结果，避免重复解码：

```bash
cinema-lab music import-receipt library/legacy/audio/ncm-decode.receipt.json
```

导入核对源音频和输出哈希，重新测量可播放文件。原回执中没有有效来源映射的记录不会凭名称猜测关联。

## 工程固定音频和歌词版本

```bash
cinema-lab init --date 2026-11-11 --slug demo --title "作品名称" \
  --recipe continuous-scroll --music "歌曲名称"

# 或给已存在的工程选择音乐：
cinema-lab music bind "歌曲名称" projects/2026-11-11/demo

# 多个歌词候选时显式指定：
cinema-lab music bind "资产ID" projects/2026-11-11/demo --lyrics-sha256 <歌词哈希>
```

工程的 `audio/music-selection.json` 记录资产 ID、音源哈希、可播放音频哈希、歌词版本与测量结果。`audio/inputs/` 存放选定文件的独立副本，文件名为哈希，不依赖可变的库软链接。旧工程已有音频哈希时必须匹配；不同音源或已锁定的不同歌词版本会报错，应建立新工程或显式版本流程。

原文与翻译的排版、字幕样式、视觉方向和分镜仍属于具体工程。通用音频分析可放在对应资产目录的 `analysis/`，并记录输入哈希和工具版本；本次提供目录规则，尚未实现自动节奏分析或 ASR 执行器。

## 校验与工作区

```bash
cinema-lab music audit
cinema-lab validate projects/2026-11-11/demo
```

资产审计检查缓存和歌词快照，以及所有工程锁定输入的哈希。新规范工程的 `validate` 也检查锁定输入，不能把历史上结构不同的制作目录自动当作符合全部 schema 的工程。

音乐命令默认以当前目录为 Lab 根目录。外部调用可使用 `cinema-lab music --workspace /path/to/lab ...`。Git 仅保存管理代码、通用 schema、空白模板、文档和合成测试。
