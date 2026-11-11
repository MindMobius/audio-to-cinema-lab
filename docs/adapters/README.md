# 工具环节说明

这里记录各制作环节的输入、输出、工具和当前能力。目录中的说明并不代表执行器已经封装；可执行实现位于 `src/cinema_lab/`。

| 环节 | 说明 |
| --- | --- |
| 音源恢复 | [audio-decoding](audio-decoding/README.md) |
| 语音转写 | [asr](asr/README.md) |
| 音频分析 | [audio-analysis](audio-analysis/README.md) |
| 文本对齐 | [alignment](alignment/README.md) |
| 人物与场景资产 | [asset-generation](asset-generation/README.md) |
| 图像生成 | [image-generation](image-generation/README.md) |
| 视频生成 | [video-generation](video-generation/README.md) |
| 镜头编排 | [editor](editor/README.md) |
| 画面与文字合成 | [composition](composition/README.md) |
| 验证与审查 | [verification](verification/README.md) |

新增执行器遵循[适配器契约](../adapters.md)，提供输入输出说明、无密钥配置示例、版本化运行入口、运行回执与不依赖私人素材的测试。工具可用时另做集成验证。

[组件状态表](../production/components.md)区分可执行命令、已有制作实践和未来计划。具体工程、素材、工具环境与运行记录均留本地。
