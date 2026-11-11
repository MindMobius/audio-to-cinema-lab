# 视频生成

## 当前状态

本地工程有ComfyUI＋MiniMax H3真实生成记录，包括Turbo 8step局部动画。通用提交、恢复和选片执行器尚未封装。

## 输入与产出

- 输入：首帧或多参考资产、动作约束、帧数与分辨率、模型私有参数。
- 产出：提交id、实际工作流、模型与LoRA、输出媒体、元数据、耗时、哈希及选片结果。

遵循[适配器约定](../../adapters.md)。参数和执行状态见[组件表](../../production/components.md)，具体制作规则见[MV手册](../../production/mv-playbook.md)。
