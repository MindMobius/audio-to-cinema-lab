# 三种制作配方

配方是可复制的创作与检查框架。`cinema-lab init --recipe ...` 会创建本地草稿及模板，不调用图像或视频模型，也不启动渲染。

| 配方id | 表现方式 | 已有实践依据 | 首要检查 |
| --- | --- | --- | --- |
| `cinematic-scenes` | 分镜叙事，人物与场景通过剪辑相连 | 早期人物资产卡与分镜制作 | 跨镜头身份、着装、动作及叙事关系 |
| `abstract-emotion` | 用空间、姿态和物件的转变呈现内在情绪 | 抽象人物和情绪空间的MV实践 | 视觉隐喻是否连贯、人物规则是否稳定 |
| `continuous-scroll` | 共享世界、局部动作、后期连续运镜 | 长卷样段、完整制作与移动开场修订 | 接缝、摄影机速度、歌词阅读、局部动作融合 |

## 初始化

```bash
cinema-lab init --date 2026-11-11 --slug experiment --title "作品名称" \
  --recipe abstract-emotion
```

默认写入 `.local/projects/2026-11-11/experiment/`。重复名称会报错，防止覆盖。日期是创建日期，后续返修仍属于原工程。

新增四份产物：

- `concept/recipe.json`：本次选用配方的快照。
- `concept/visual-direction.md`：视觉方向、风格锁定、资产树和样段决策模板。
- `edit/caption-profile.json`：电影双语字幕或场景中括号字幕的参考设置。
- `verification/review-plan.json`：计划覆盖率、技术检查、视觉审查及实际审查范围。

`status`、`render_runner` 和审查计划中的 `enforcement` 明确表明运行边界。写入模板不代表生成完成，`validate` 通过也不代表美术或全片验收。

配方不绑定模型。人物资产可来自图像生成、社区参考或已有资产库；视频模型和合成器按作品需求配置。不要把同一种色调和同一种运动机械套用到所有歌曲。
